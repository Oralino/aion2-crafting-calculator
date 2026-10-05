import math

import pytest

from aion2calc.calc import sale


def test_profit_after_tax() -> None:
    result = sale(total_cost=8_000, sell_price=10_000, sell_tax=0.1)
    assert result.tax == pytest.approx(1_000)
    assert result.net == pytest.approx(9_000)
    assert result.profit == pytest.approx(1_000)


def test_loss_is_negative() -> None:
    assert sale(12_000, 10_000, 0.0).profit == pytest.approx(-2_000)


@pytest.mark.parametrize(("price", "tax"), [(-1, 0.1), (100, 1.0), (100, -0.1), (100, math.nan)])
def test_bad_inputs_rejected(price: int, tax: float) -> None:
    with pytest.raises(ValueError):
        sale(0, price, tax)
