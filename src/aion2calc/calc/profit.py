"""Profit from selling the finished items, after the sell-side (market) tax.

The top tier's successful crafts also have a combo chance of giving the Splendent version, which
sells for more, so the sale is an expected value: (1 − combo) × normal price + combo × Splendent
price, per item.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Sale:
    gross: float
    """Expected sale price of all items, before tax."""
    tax: float
    net: float
    profit: float
    """Net sale minus total cost; negative is a loss."""


def sale(
    total_cost: float,
    sell_price: int,
    sell_tax: float,
    combo_price: int | None = None,
    combo_rate: float = 0.0,
    items: float = 1.0,
) -> Sale:
    """`sell_tax` and `combo_rate` are fractions (0.1 = 10%). Without a `combo_price` every item
    sells at `sell_price`. `items` is how many final items the cost bought."""
    for name, price in (("sell_price", sell_price), ("combo_price", combo_price)):
        if price is not None and price < 0:
            raise ValueError(f"{name} must not be negative, got {price}")
    if not (math.isfinite(sell_tax) and 0 <= sell_tax < 1):
        raise ValueError(f"sell_tax must be a fraction in [0, 1), got {sell_tax}")
    if not (math.isfinite(combo_rate) and 0 <= combo_rate <= 1):
        raise ValueError(f"combo_rate must be a fraction in [0, 1], got {combo_rate}")
    per_item = float(sell_price)
    if combo_price is not None:
        per_item = (1 - combo_rate) * sell_price + combo_rate * combo_price
    gross = per_item * items
    tax = gross * sell_tax
    net = gross - tax
    return Sale(gross, tax, net, net - total_cost)
