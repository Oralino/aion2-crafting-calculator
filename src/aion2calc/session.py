"""The open craft: a recipe chain plus the user's inputs, turned into calc objects. No Qt here.

The UI edits a CraftSession and asks it for rows and results; prices will come from the SQLite store
and OCR later, for now they're the user's manual entries.
"""

import math
from dataclasses import dataclass
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
from aion2calc.data.recipes import Catalog, Recipe

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
    MANUAL = "manual"
    MISSING = "missing"
    CRAFTED = "crafted"
    """The Splendent item made by the tier below; not bought."""


@dataclass(frozen=True)
class MaterialRow:
    item_id: int
    name: str
    qty: int
    unit_price: int | None
    source: Source
    excluded: bool

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
    ) -> None:
        self.catalog = catalog
        self.settings = settings or Settings()
        self.tiers = [TierSettings(r) for r in catalog.chain(item_id)]
        self.prices: dict[int, int] = dict(prices or {})
        """Manual unit prices by item id, shared by every tier (and recipe) that uses the item."""
        self.excluded: set[tuple[int, int]] = set()
        """(tier index, item id) pairs left out of the cost."""
        self.sell_price: int | None = None
        # Each tier above the first uses up the combo item made by the tier below it.
        self._crafted = {
            index + 1: tier.recipe.combo_item_id
            for index, tier in enumerate(self.tiers[:-1])
            if tier.recipe.combo_item_id is not None
        }

    @property
    def final_item(self) -> int:
        return self.tiers[-1].recipe.item_id

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
            price = self.prices.get(item_id)
            if item_id == crafted:
                source = Source.CRAFTED
            else:
                source = Source.MANUAL if price is not None else Source.MISSING
            rows.append(
                MaterialRow(
                    item_id,
                    self.name(item_id),
                    ingredient.qty,
                    price,
                    source,
                    (tier_index, item_id) in self.excluded,
                )
            )
        return rows

    def set_price(self, item_id: int, price: int | None) -> None:
        if price is None:
            self.prices.pop(item_id, None)
        else:
            self.prices[item_id] = check_kinah(price)

    def set_sell_price(self, price: int | None) -> None:
        self.sell_price = None if price is None else check_kinah(price)

    def set_chance(self, tier_index: int, chance: float | None) -> None:
        """None means not entered (counted as 100%)."""
        self.tiers[tier_index].chance = None if chance is None else check_rate(chance, "chance")

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
                )
                for row in self.rows(index)
            )
            tiers.append(
                Tier(
                    self.name(settings.recipe.item_id),
                    materials,
                    chance=settings.chance,
                    combo_rate=settings.combo_rate,
                )
            )
        return Craft(self.name(self.final_item), tuple(tiers))

    def cost(self) -> CostBreakdown:
        return craft_cost(self.craft(), self.settings.buy_tax)

    def sale(self) -> Sale | None:
        if self.sell_price is None:
            return None
        return sale(self.cost().total, self.sell_price, self.settings.sell_tax)

    def warnings(self) -> list[str]:
        missing = {
            row.item_id
            for index in range(len(self.tiers))
            for row in self.rows(index)
            if row.source is Source.MISSING and not row.excluded
        }
        no_chance = sum(1 for t in self.tiers if t.chance is None)
        notes = []
        if missing:
            noun = "material has" if len(missing) == 1 else "materials have"
            notes.append(f"{len(missing)} {noun} no price (counted as 0)")
        if no_chance:
            noun = "tier has" if no_chance == 1 else "tiers have"
            notes.append(f"{no_chance} {noun} no craft chance (counted as 100%)")
        return notes
