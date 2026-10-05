"""Crafting cost: needed crafts per tier, material exclusions and buy-side tax."""

import math
from dataclasses import dataclass


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


@dataclass(frozen=True)
class Tier:
    name: str
    target: int
    """How many successful crafts are wanted."""
    materials: tuple[Material, ...]
    chance: float | None = None
    """Craft success rate in (0, 1]; None means every craft succeeds."""

    def __post_init__(self) -> None:
        if self.target < 0:
            raise ValueError(f"{self.name}: target must not be negative")
        if self.chance is not None and not 0 < self.chance <= 1:
            raise ValueError(f"{self.name}: chance must be in (0, 1], got {self.chance}")

    @property
    def needed(self) -> float:
        """Expected number of attempts to reach the target."""
        return self.target / self.chance if self.chance is not None else float(self.target)

    @property
    def cost_per_craft(self) -> int:
        return sum(m.cost for m in self.materials if not m.excluded)

    @property
    def cost(self) -> float:
        return self.needed * self.cost_per_craft


@dataclass(frozen=True)
class Craft:
    name: str
    tiers: tuple[Tier, ...]


@dataclass(frozen=True)
class CostBreakdown:
    tier_costs: tuple[float, ...]
    subtotal: float
    tax: float
    total: float


def craft_cost(craft: Craft, buy_tax: float = 0.0) -> CostBreakdown:
    """Total cost of a craft. `buy_tax` is a fraction (0.1 = 10%) applied to the subtotal."""
    if not (math.isfinite(buy_tax) and buy_tax >= 0):
        raise ValueError(f"buy_tax must be a finite, non-negative fraction, got {buy_tax}")
    tier_costs = tuple(tier.cost for tier in craft.tiers)
    subtotal = sum(tier_costs)
    tax = subtotal * buy_tax
    return CostBreakdown(tier_costs, subtotal, tax, subtotal + tax)
