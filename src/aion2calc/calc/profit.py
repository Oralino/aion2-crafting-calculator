"""Profit from selling the finished item, after the sell-side (market) tax."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Sale:
    price: int
    tax: float
    net: float
    profit: float
    """Net sale minus total cost; negative is a loss."""


def sale(total_cost: float, sell_price: int, sell_tax: float) -> Sale:
    """`sell_tax` is a fraction (0.1 = 10%) taken from the sale price."""
    if sell_price < 0:
        raise ValueError(f"sell_price must not be negative, got {sell_price}")
    if not (math.isfinite(sell_tax) and 0 <= sell_tax < 1):
        raise ValueError(f"sell_tax must be a fraction in [0, 1), got {sell_tax}")
    tax = sell_price * sell_tax
    net = sell_price - tax
    return Sale(sell_price, tax, net, net - total_cost)
