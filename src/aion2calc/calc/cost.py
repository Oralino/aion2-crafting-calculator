"""Crafting cost of a combo chain: needed crafts per tier, material exclusions and buy-side tax.

A craft is a chain of tiers (e.g. Ruby Necklace → Expert's → Artisan's → Star Dragon Lord). Each
successful craft of a tier has a combo chance to produce the "Splendent" item instead, and every
attempt at the next tier uses up one of those, failed attempts included. So, from the final tier
down: combo items needed = the next tier's attempts, and successes needed = that ÷ combo rate.
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
    """Share of successes that combo into the next tier's item. Unused on the final tier."""

    def __post_init__(self) -> None:
        if self.chance is not None:
            _check_rate(self.name, "chance", self.chance)
        _check_rate(self.name, "combo_rate", self.combo_rate)

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

    def __post_init__(self) -> None:
        if self.target < 0:
            raise ValueError(f"{self.name}: target must not be negative")


@dataclass(frozen=True)
class TierCost:
    """Expected averages, so `successes` and `attempts` can be fractional (e.g. 68.7 crafts)."""

    tier: Tier
    successes: float
    attempts: float
    cost: float
    lost: float
    """Part of `cost` spent on crafts that didn't move up a tier (failures, non-combo results)."""


@dataclass(frozen=True)
class CostBreakdown:
    tiers: tuple[TierCost, ...]
    subtotal: float
    lost: float
    """Sum of the tiers' lost value; part of `subtotal`, before tax."""
    tax: float
    total: float


def required_successes(craft: Craft) -> tuple[float, ...]:
    """Successful crafts needed per tier, lowest tier first. With every chance at 100% and a 25%
    combo this is 64, 16, 4, 1; failures at a tier raise the counts of every tier below it."""
    if not craft.tiers:
        return ()
    needed = [float(craft.target)]
    upper = craft.tiers[-1]
    for lower in reversed(craft.tiers[:-1]):
        combo_items = upper.attempts(needed[-1])
        needed.append(combo_items / lower.combo_rate)
        upper = lower
    return tuple(reversed(needed))


def craft_cost(craft: Craft, buy_tax: float = 0.0) -> CostBreakdown:
    """Total cost of a craft. `buy_tax` is a fraction (0.1 = 10%) applied to the subtotal."""
    if not (math.isfinite(buy_tax) and buy_tax >= 0):
        raise ValueError(f"buy_tax must be a finite, non-negative fraction, got {buy_tax}")
    successes = required_successes(craft)
    attempts = [tier.attempts(n) for tier, n in zip(craft.tiers, successes, strict=True)]
    # Crafts that move up: the combo items the next tier's attempts use, or the final items.
    useful = (*attempts[1:], float(craft.target)) if attempts else ()
    tier_costs = []
    for tier, needed, tries, kept in zip(craft.tiers, successes, attempts, useful, strict=True):
        cost = tries * tier.cost_per_craft
        lost = cost * (1 - kept / tries) if tries else 0.0
        tier_costs.append(TierCost(tier, needed, tries, cost, lost))
    subtotal = sum(t.cost for t in tier_costs)
    lost = sum(t.lost for t in tier_costs)
    tax = subtotal * buy_tax
    return CostBreakdown(tuple(tier_costs), subtotal, lost, tax, subtotal + tax)
