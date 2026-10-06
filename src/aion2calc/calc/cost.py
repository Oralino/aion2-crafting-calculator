"""Crafting cost of a combo chain: needed crafts per tier, material exclusions and buy-side tax.

A craft is a chain of tiers (e.g. Ruby Necklace → Expert's → Artisan's → Star Dragon Lord). Each
successful craft of a tier has a combo chance to produce the "Splendent" item instead, and every
attempt at the next tier uses up one of those, failed attempts included. So, from the final tier
down: combo items needed = the next tier's attempts, and successes needed = that ÷ combo rate.

A tier's crafts can also be planned by the user; the tiers below then supply what those crafts
need. And when the Splendent piece a tier uses was bought or valued instead of crafted, the tiers
below it aren't counted (`Craft.first_tier`), so nothing is paid for twice.
"""

import math
from dataclasses import dataclass

DEFAULT_COMBO_RATE = 0.25


@dataclass(frozen=True)
class Material:
    name: str
    qty: int
    unit_price: int | None
    """Kinah per unit; None means no market price, which counts as 0."""
    excluded: bool = False
    """Left out of the cost sum (e.g. already owned)."""

    def __post_init__(self) -> None:
        if self.qty < 0:
            raise ValueError(f"{self.name}: qty must not be negative")
        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError(f"{self.name}: unit_price must not be negative")

    @property
    def cost(self) -> int:
        return 0 if self.unit_price is None else self.qty * self.unit_price


def _check_rate(owner: str, field: str, value: float) -> None:
    if not 0 < value <= 1:
        raise ValueError(f"{owner}: {field} must be in (0, 1], got {value}")


@dataclass(frozen=True)
class Tier:
    name: str
    materials: tuple[Material, ...]
    chance: float | None = None
    """Craft success rate in (0, 1]; None means every craft succeeds."""
    combo_rate: float = DEFAULT_COMBO_RATE
    """Share of successes that combo into the Splendent item. Below the top tier it feeds the next
    tier; on the top tier it only affects the expected sale (see calc.profit), not the cost."""
    crafts: float | None = None
    """Crafts the user plans for this tier; None means as many as the chain needs."""

    def __post_init__(self) -> None:
        if self.chance is not None:
            _check_rate(self.name, "chance", self.chance)
        _check_rate(self.name, "combo_rate", self.combo_rate)
        if self.crafts is not None and not (math.isfinite(self.crafts) and self.crafts >= 0):
            raise ValueError(f"{self.name}: crafts must be a non-negative number")

    @property
    def success_rate(self) -> float:
        return 1.0 if self.chance is None else self.chance

    @property
    def cost_per_craft(self) -> int:
        return sum(m.cost for m in self.materials if not m.excluded)

    def attempts(self, successes: float) -> float:
        """Expected crafts to reach `successes` successful crafts."""
        return successes / self.chance if self.chance is not None else successes


@dataclass(frozen=True)
class Craft:
    name: str
    tiers: tuple[Tier, ...]
    """Lowest tier first; the last tier makes the final item."""
    target: int = 1
    """How many final items are wanted."""
    first_tier: int = 0
    """Tiers below this index aren't counted: the Splendent piece this tier uses was bought or
    valued instead of crafted."""

    def __post_init__(self) -> None:
        if self.target < 0:
            raise ValueError(f"{self.name}: target must not be negative")
        if not 0 <= self.first_tier <= max(len(self.tiers) - 1, 0):
            raise ValueError(f"{self.name}: first_tier out of range")


@dataclass(frozen=True)
class TierCost:
    """Expected averages, so `successes` and `attempts` can be fractional (e.g. 68.7 crafts)."""

    tier: Tier
    successes: float
    attempts: float
    cost: float
    lost: float
    """Part of `cost` spent on crafts that didn't move up a tier (failures, non-combo results)."""
    counted: bool = True
    """False below `Craft.first_tier`: shown for reference, costs nothing."""

    @property
    def combos(self) -> float:
        """Expected successes that combo into the Splendent item."""
        return self.successes * self.tier.combo_rate


@dataclass(frozen=True)
class CostBreakdown:
    tiers: tuple[TierCost, ...]
    subtotal: float
    lost: float
    """Sum of the tiers' lost value; part of `subtotal`, before tax."""
    tax: float
    total: float


def plan(craft: Craft) -> tuple[tuple[float, float], ...]:
    """(attempts, expected successes) per tier, lowest tier first, worked out from the top down.

    The top tier needs `target` successes unless its crafts are planned; each lower tier must make
    one combo item per attempt of the tier above (failures use it up too). A planned tier uses its
    planned crafts, and its successes follow from its chance."""
    out: list[tuple[float, float]] = []
    items_needed = float(craft.target)  # successes the tier being worked out must produce
    for index in range(len(craft.tiers) - 1, -1, -1):
        tier = craft.tiers[index]
        if index < len(craft.tiers) - 1:
            items_needed /= tier.combo_rate  # only combo results move up
        attempts = tier.crafts if tier.crafts is not None else tier.attempts(items_needed)
        out.append((attempts, attempts * tier.success_rate))
        items_needed = attempts  # the tier below supplies one combo item per attempt here
    return tuple(reversed(out))


def required_successes(craft: Craft) -> tuple[float, ...]:
    """Expected successful crafts per tier, lowest tier first. With every chance at 100% and a
    25% combo this is 64, 16, 4, 1; failures at a tier raise the counts of every tier below it."""
    return tuple(successes for _, successes in plan(craft))


def craft_cost(craft: Craft, buy_tax: float = 0.0) -> CostBreakdown:
    """Total cost of a craft. `buy_tax` is a fraction (0.1 = 10%) applied to the subtotal."""
    if not (math.isfinite(buy_tax) and buy_tax >= 0):
        raise ValueError(f"buy_tax must be a finite, non-negative fraction, got {buy_tax}")
    steps = plan(craft)
    # Crafts that move up: the combo items the next tier's attempts use, or the top's successes.
    useful = [attempts for attempts, _ in steps[1:]] + ([steps[-1][1]] if steps else [])
    tier_costs = []
    for index, (tier, (tries, successes), kept) in enumerate(
        zip(craft.tiers, steps, useful, strict=True)
    ):
        if index < craft.first_tier:
            tier_costs.append(TierCost(tier, successes, tries, 0.0, 0.0, counted=False))
            continue
        cost = tries * tier.cost_per_craft
        lost = min(cost, max(0.0, cost * (1 - kept / tries))) if tries else 0.0
        tier_costs.append(TierCost(tier, successes, tries, cost, lost))
    subtotal = sum(t.cost for t in tier_costs)
    lost = sum(t.lost for t in tier_costs)
    tax = subtotal * buy_tax
    return CostBreakdown(tuple(tier_costs), subtotal, lost, tax, subtotal + tax)
