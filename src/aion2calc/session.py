"""The open craft: a recipe chain plus the user's inputs, turned into calc objects. No Qt here.

The UI edits a CraftSession and asks it for rows and results. A material's price is the user's
manual price if set, else the newest market (OCR) reading, else missing (counted as 0). A capture
clears the typed price (material or sell price) of each item it reads, so the newest price wins.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from aion2calc.calc import (
    DEFAULT_COMBO_RATE,
    CostBreakdown,
    Craft,
    Material,
    Sale,
    Tier,
    craft_cost,
    sale,
)
from aion2calc.data.prices import Observation
from aion2calc.data.recipes import Catalog, Recipe

MAX_CRAFTS = 1_000_000
"""Upper bound for planned crafts per tier."""

MAX_KINAH = 10**13 - 1
"""Upper bound for any typed price: far above real prices, and keeps float maths exact enough."""


def check_rate(value: float, name: str) -> float:
    """A success or combo rate: a fraction in (0, 1]."""
    if not (math.isfinite(value) and 0 < value <= 1):
        raise ValueError(f"{name} must be above 0% and at most 100%")
    return value


def check_tax(value: float) -> float:
    """A tax: a fraction in [0, 1)."""
    if not (math.isfinite(value) and 0 <= value < 1):
        raise ValueError("tax must be from 0% up to (not including) 100%")
    return value


def check_kinah(value: int) -> int:
    if not 0 <= value <= MAX_KINAH:
        raise ValueError(f"Kinah amount must be from 0 to {MAX_KINAH:,}")
    return value


class Source(Enum):
    OCR = "ocr"
    """Newest market reading."""
    MANUAL = "manual"
    MISSING = "missing"
    CRAFTED = "crafted"
    """The Splendent item made by the tier below; not bought."""
    VALUED = "valued"
    """That Splendent item, with a value the user entered (bought, or what it cost them)."""


@dataclass(frozen=True)
class MaterialRow:
    item_id: int
    name: str
    qty: int
    unit_price: int | None
    source: Source
    excluded: bool
    observed_at: datetime | None = None
    """When an OCR price was read."""

    @property
    def total(self) -> int | None:
        if self.source is Source.CRAFTED or self.unit_price is None:
            return None
        return self.qty * self.unit_price


@dataclass
class TierSettings:
    recipe: Recipe
    chance: float | None = None
    """In-game success rate; None until the user enters it (counted as 100%)."""
    combo_rate: float = DEFAULT_COMBO_RATE
    crafts: int | None = None
    """Crafts the user plans for this tier; None means as many as the chain needs."""


@dataclass
class Settings:
    buy_tax: float = 0.10
    sell_tax: float = 0.10

    def __post_init__(self) -> None:
        check_tax(self.buy_tax)
        check_tax(self.sell_tax)

    def set_buy_tax(self, value: float) -> None:
        self.buy_tax = check_tax(value)

    def set_sell_tax(self, value: float) -> None:
        self.sell_tax = check_tax(value)


class CraftSession:
    def __init__(
        self,
        catalog: Catalog,
        item_id: int,
        settings: Settings | None = None,
        prices: dict[int, int] | None = None,
        market: dict[int, Observation] | None = None,
    ) -> None:
        self.catalog = catalog
        self.settings = settings or Settings()
        self.tiers = [TierSettings(r) for r in catalog.chain(item_id)]
        self.prices: dict[int, int] = dict(prices or {})
        """Manual unit prices by item id, shared by every tier (and recipe) that uses the item."""
        self.market: dict[int, Observation] = dict(market or {})
        """Newest market (OCR) reading per item id."""
        self.crafted_values: dict[int, int] = {}
        """Value per unit of the Splendent piece a tier uses, by tier index, when the user bought it
        or knows what it cost them. The tiers below that one then aren't counted."""
        self.on_manual_price: Callable[[int, int | None], None] | None = None
        """Called after a manual price is set or cleared (the window saves it)."""
        self.excluded: set[tuple[int, int]] = set()
        """(tier index, item id) pairs left out of the cost."""
        self.sell_price: int | None = None
        """Market price of the normal final item."""
        self.combo_sell_price: int | None = None
        """Market price of the final item's Splendent (combo) version, if it has one."""
        # Each tier above the first uses up the combo item made by the tier below it.
        self._crafted = {
            index + 1: tier.recipe.combo_item_id
            for index, tier in enumerate(self.tiers[:-1])
            if tier.recipe.combo_item_id is not None
        }

    @property
    def final_item(self) -> int:
        return self.tiers[-1].recipe.item_id

    @property
    def final_combo_item(self) -> int | None:
        """The Splendent version the top tier can combo into, if any."""
        return self.tiers[-1].recipe.combo_item_id

    def name(self, item_id: int) -> str:
        return self.catalog.name(item_id)

    def grade(self, item_id: int) -> str | None:
        item = self.catalog.items.get(item_id)
        return item.grade if item else None

    def rows(self, tier_index: int) -> list[MaterialRow]:
        crafted = self._crafted.get(tier_index)
        rows = []
        for ingredient in self.tiers[tier_index].recipe.ingredients:
            item_id = ingredient.item_id
            price, source, observed = self.price(item_id)
            if item_id == crafted:
                value = self.crafted_values.get(tier_index)
                source = Source.CRAFTED if value is None else Source.VALUED
                price, observed = value, None
            rows.append(
                MaterialRow(
                    item_id,
                    self.name(item_id),
                    ingredient.qty,
                    price,
                    source,
                    (tier_index, item_id) in self.excluded,
                    observed,
                )
            )
        return rows

    def price(self, item_id: int) -> tuple[int | None, Source, datetime | None]:
        """(unit price, where it came from, when it was read): manual, else market, else missing."""
        if item_id in self.prices:
            return self.prices[item_id], Source.MANUAL, None
        if (seen := self.market.get(item_id)) is not None:
            return seen.unit_price, Source.OCR, seen.observed_at
        return None, Source.MISSING, None

    def set_price(self, item_id: int, price: int | None) -> None:
        """Set or clear a manual price (clearing falls back to the market price)."""
        if price is None:
            self.prices.pop(item_id, None)
        else:
            self.prices[item_id] = check_kinah(price)
        if self.on_manual_price is not None:
            self.on_manual_price(item_id, price)

    def effective_sell_price(self, combo: bool = False) -> int | None:
        """The typed sell price, else the market price of the finished item."""
        typed = self.combo_sell_price if combo else self.sell_price
        return typed if typed is not None else self.market_sell_price(combo)

    def market_sell_price(self, combo: bool = False) -> int | None:
        """The finished item's (or its Splendent version's) newest market price, if read."""
        item_id = self.final_combo_item if combo else self.final_item
        seen = self.market.get(item_id) if item_id is not None else None
        return seen.unit_price if seen else None

    def set_sell_price(self, price: int | None) -> None:
        self.sell_price = None if price is None else check_kinah(price)

    def set_combo_sell_price(self, price: int | None) -> None:
        self.combo_sell_price = None if price is None else check_kinah(price)

    def clear_captured_sell_prices(self, item_ids: set[int]) -> bool:
        """Drop typed sell prices of finished items a capture just read (the newest price wins).
        Returns whether any was dropped."""
        dropped = False
        if self.sell_price is not None and self.final_item in item_ids:
            self.sell_price, dropped = None, True
        if self.combo_sell_price is not None and self.final_combo_item in item_ids:
            self.combo_sell_price, dropped = None, True
        return dropped

    def set_chance(self, tier_index: int, chance: float | None) -> None:
        """None means not entered (counted as 100%)."""
        self.tiers[tier_index].chance = None if chance is None else check_rate(chance, "chance")

    def set_crafts(self, tier_index: int, crafts: int | None) -> None:
        """Plan this tier's crafts; None goes back to what the chain needs."""
        if crafts is not None and not 0 <= crafts <= MAX_CRAFTS:
            raise ValueError(f"crafts must be from 0 to {MAX_CRAFTS:,}")
        self.tiers[tier_index].crafts = crafts

    def has_crafted_input(self, tier_index: int) -> bool:
        return tier_index in self._crafted

    def set_crafted_value(self, tier_index: int, value: int | None) -> None:
        """Value the Splendent piece this tier uses (None: craft it in the tiers below again)."""
        if tier_index not in self._crafted:
            raise ValueError("this tier doesn't use a Splendent piece from a tier below")
        if value is None:
            self.crafted_values.pop(tier_index, None)
        else:
            self.crafted_values[tier_index] = check_kinah(value)

    @property
    def first_tier(self) -> int:
        """The lowest tier that's counted: the highest tier whose Splendent input has a value."""
        return max(self.crafted_values, default=0)

    def counted(self, tier_index: int) -> bool:
        return tier_index >= self.first_tier

    def set_combo_rate(self, tier_index: int, rate: float) -> None:
        self.tiers[tier_index].combo_rate = check_rate(rate, "combo rate")

    def set_excluded(self, tier_index: int, item_id: int, excluded: bool) -> None:
        key = (tier_index, item_id)
        if excluded:
            self.excluded.add(key)
        else:
            self.excluded.discard(key)

    def craft(self) -> Craft:
        tiers = []
        for index, settings in enumerate(self.tiers):
            materials = tuple(
                Material(
                    row.name,
                    row.qty,
                    row.unit_price,
                    excluded=row.excluded or row.source is Source.CRAFTED,
                    # a VALUED Splendent piece counts at its value like any bought material
                )
                for row in self.rows(index)
            )
            tiers.append(
                Tier(
                    self.name(settings.recipe.item_id),
                    materials,
                    chance=settings.chance,
                    combo_rate=settings.combo_rate,
                    crafts=settings.crafts,
                )
            )
        return Craft(self.name(self.final_item), tuple(tiers), first_tier=self.first_tier)

    def cost(self) -> CostBreakdown:
        return craft_cost(self.craft(), self.settings.buy_tax)

    def sale(self) -> Sale | None:
        """Expected sale of the final items. The top tier's combo chance gives the Splendent
        version; without its price, it's valued at the normal price."""
        sell_price = self.effective_sell_price()
        if sell_price is None:
            return None
        has_combo = self.final_combo_item is not None
        cost = craft_cost(self.craft(), self.settings.buy_tax)
        return sale(
            cost.total,
            sell_price,
            self.settings.sell_tax,
            combo_price=self.effective_sell_price(combo=True) if has_combo else None,
            combo_rate=self.tiers[-1].combo_rate if has_combo else 0.0,
            # Items the top tier is expected to make: the target, or what planned crafts give.
            items=cost.tiers[-1].successes,
        )

    def warnings(self) -> list[str]:
        missing = {
            row.item_id
            for index in range(self.first_tier, len(self.tiers))
            for row in self.rows(index)
            if row.source is Source.MISSING and not row.excluded
        }
        no_chance = sum(1 for t in self.tiers[self.first_tier :] if t.chance is None)
        notes = []
        if missing:
            noun = "material has" if len(missing) == 1 else "materials have"
            notes.append(f"{len(missing)} {noun} no price (counted as 0)")
        if no_chance:
            noun = "tier has" if no_chance == 1 else "tiers have"
            notes.append(f"{no_chance} {noun} no craft chance (counted as 100%)")
        # Planned crafts can leave a tier short of the Splendent pieces the tier above uses up.
        steps = self.cost().tiers
        for index in range(self.first_tier, len(steps) - 1):
            if steps[index].combos < steps[index + 1].attempts * (1 - 1e-9):
                name = self.name(self.tiers[index].recipe.item_id)
                notes.append(f"{name} makes fewer Splendent pieces than the tier above uses")
        sell, combo = self.effective_sell_price(), self.effective_sell_price(combo=True)
        if sell is not None and self.final_combo_item is not None:
            if combo is None:
                notes.append("No Splendent sell price (valued at the normal price)")
            elif combo < sell:
                notes.append("Splendent sell price is below the normal price; typo?")
        return notes
