import math

import pytest

from aion2calc.calc import sale


def test_profit_after_tax() -> None:
    result = sale(total_cost=8_000, sell_price=10_000, sell_tax=0.1)
    assert result.gross == 10_000
    assert result.tax == pytest.approx(1_000)
    assert result.net == pytest.approx(9_000)
    assert result.profit == pytest.approx(1_000)


def test_loss_is_negative() -> None:
    assert sale(12_000, 10_000, 0.0).profit == pytest.approx(-2_000)


def test_top_tier_combo_is_an_expected_value() -> None:
    # 75% sell at 10,000, 25% (Splendent) at 30,000: 15,000 expected, 13,500 after 10% tax.
    result = sale(10_000, 10_000, 0.1, combo_price=30_000, combo_rate=0.25)
    assert result.gross == pytest.approx(15_000)
    assert result.profit == pytest.approx(3_500)


def test_without_combo_price_the_rate_is_ignored() -> None:
    assert sale(0, 10_000, 0.0, combo_rate=0.25).gross == 10_000


def test_several_items() -> None:
    assert sale(0, 1_000, 0.0, items=3).gross == 3_000


@pytest.mark.parametrize(
    ("price", "tax", "combo_price", "rate"),
    [
        (-1, 0.1, None, 0.0),
        (100, 1.0, None, 0.0),
        (100, -0.1, None, 0.0),
        (100, math.nan, None, 0.0),
        (100, 0.1, -5, 0.25),
        (100, 0.1, 200, 1.5),
    ],
)
def test_bad_inputs_rejected(price: int, tax: float, combo_price: int | None, rate: float) -> None:
    with pytest.raises(ValueError):
        sale(0, price, tax, combo_price, rate)


@pytest.mark.parametrize(("rate", "gross"), [(0.0, 1_000), (1.0, 4_000)])
def test_combo_rate_boundaries(rate: float, gross: float) -> None:
    assert sale(0, 1_000, 0.0, combo_price=4_000, combo_rate=rate, items=1).gross == gross


def test_several_items_with_combo() -> None:
    assert sale(0, 1_000, 0.0, combo_price=3_000, combo_rate=0.5, items=2).gross == 4_000
