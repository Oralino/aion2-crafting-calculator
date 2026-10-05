import math
from dataclasses import replace

import pytest

from aion2calc.calc import Craft, Material, Tier, craft_cost, required_successes

# The owner's Google Sheet, "Accessories" tab. Expected values are the sheet's own results; its
# 64/16/4/1 counts follow from the default 25% combo rate.
ACCESSORIES = Craft(
    "Accessory",
    (
        Tier(
            "Grey",
            (
                Material("Diamond Decoration", 1, None),
                Material("Refining stone", 3, 4_000),
                Material("Odyle", 1, None),
            ),
            chance=0.93121326,
        ),
        Tier(
            "Green",
            (
                Material("Expert's Refining stone", 3, 45_000),
                Material("Fine Diamond Gemstone", 3, 3_000),
                Material("Fine Odyle", 2, 3_000),
            ),
            chance=0.94633946,
        ),
        Tier(
            "Blue",
            (
                Material("Artisan's Refining stone", 3, 300_000),
                Material("Pure Diamond Gemstone", 4, 50_000),
                Material("Pure Odyle", 2, 85_000),
            ),
            chance=0.96837241,
        ),
        Tier(
            "Legendary",
            (
                Material("Artisan's Ultimate Refining stone", 2, 250_000, excluded=True),
                Material("Enhanced Thick Balaur", 11, 40_000, excluded=True),
                Material("Wrathful Mind", 5, 370_000),
                Material("Radiant Diamond Gemstone", 5, 85_000),
                Material("Radiant Odyle", 2, 200_000),
            ),
            chance=0.94639789,
        ),
    ),
)


def tier(cost: int = 100, chance: float | None = None, combo_rate: float = 0.25) -> Tier:
    return Tier("t", (Material("m", 1, cost),), chance=chance, combo_rate=combo_rate)


def test_accessories_matches_sheet() -> None:
    result = craft_cost(ACCESSORIES, buy_tax=0.1)
    assert [t.successes for t in result.tiers] == [64, 16, 4, 1]
    assert [t.attempts for t in result.tiers] == pytest.approx(
        [68.72754368, 16.90725229, 4.13064226, 1.056638028]
    )
    expected_costs = [824_730.5241, 2_536_087.843, 5_245_915.67, 2_826_506.724]
    assert [t.cost for t in result.tiers] == pytest.approx(expected_costs, abs=0.01)
    assert result.subtotal == pytest.approx(11_433_240.76, abs=0.01)
    grey = result.tiers[0]
    assert grey.lost == pytest.approx(grey.cost * (1 - 16 / 68.72754368))
    assert result.lost == pytest.approx(sum(t.lost for t in result.tiers))
    assert all(0 <= t.lost <= t.cost for t in result.tiers)
    assert result.total == pytest.approx(12_576_564.84, abs=0.01)


def test_successes_follow_each_tiers_combo_rate() -> None:
    craft = Craft("c", (tier(combo_rate=0.5), tier(combo_rate=0.2), tier()), target=2)
    # Final tier: 2; middle: 2 / 0.2 = 10; lowest: 10 / 0.5 = 20. The final tier's rate is unused.
    assert required_successes(craft) == pytest.approx((20, 10, 2))


def test_lost_value_is_cost_of_crafts_that_dont_move_up() -> None:
    craft = Craft("c", (tier(cost=100, chance=0.5), tier(cost=1_000, chance=0.5)))
    low, final = craft_cost(craft).tiers
    # Low: 4 successes / 0.5 = 8 attempts, 1 combo moves up -> 7 of 8 crafts lost.
    assert low.cost == 800
    assert low.lost == pytest.approx(700)
    # Final: 1 success / 0.5 = 2 attempts, 1 is the item -> 1 of 2 lost.
    assert final.cost == 2_000
    assert final.lost == pytest.approx(1_000)


def test_without_failures_only_non_combo_results_are_lost() -> None:
    low, final = craft_cost(Craft("c", (tier(), tier()), target=2)).tiers
    # 8 successes, 2 combo up: 75% lost. The final tier keeps everything it makes.
    assert low.lost == pytest.approx(low.cost * 0.75)
    assert final.lost == 0


def test_no_loss_with_certain_success_and_combo() -> None:
    result = craft_cost(Craft("c", (tier(chance=1.0, combo_rate=1.0), tier(chance=1.0))))
    assert result.lost == 0


def test_attempts_divide_by_chance() -> None:
    assert tier(chance=0.5).attempts(64) == 128
    assert tier(chance=1.0).attempts(64) == 64
    assert tier().attempts(64) == 64


def test_zero_target_costs_nothing() -> None:
    result = craft_cost(Craft("c", (tier(), tier()), target=0))
    assert result.total == 0
    assert result.lost == 0
    assert [t.attempts for t in result.tiers] == [0, 0]


def test_buy_tax_on_round_numbers() -> None:
    result = craft_cost(Craft("c", (tier(cost=500),), target=2), buy_tax=0.1)
    assert result.subtotal == 1_000
    assert result.tax == pytest.approx(100)
    assert result.total == pytest.approx(1_100)


def test_empty_craft_costs_nothing() -> None:
    assert craft_cost(Craft("c", ())).total == 0


def test_excluded_and_unpriced_materials_cost_nothing() -> None:
    t = Tier(
        "t",
        (
            Material("priced", 2, 100),
            Material("excluded", 5, 1_000, excluded=True),
            Material("no price", 3, None),
        ),
    )
    assert t.cost_per_craft == 200


def test_exclusion_toggle_changes_cost() -> None:
    excluded = Material("m", 2, 100, excluded=True)
    t = Tier("t", (excluded,))
    assert t.cost_per_craft == 0
    assert replace(t, materials=(replace(excluded, excluded=False),)).cost_per_craft == 200


@pytest.mark.parametrize("rate", [0.0, -0.1, 1.5, math.nan])
def test_invalid_chance_rejected(rate: float) -> None:
    with pytest.raises(ValueError):
        tier(chance=rate)


@pytest.mark.parametrize("rate", [0.0, -0.1, 1.5, math.nan])
def test_invalid_combo_rate_rejected(rate: float) -> None:
    with pytest.raises(ValueError):
        tier(combo_rate=rate)


def test_negative_target_rejected() -> None:
    with pytest.raises(ValueError):
        Craft("c", (), target=-1)


@pytest.mark.parametrize(("qty", "price"), [(-1, 100), (1, -100)])
def test_negative_material_values_rejected(qty: int, price: int) -> None:
    with pytest.raises(ValueError):
        Material("m", qty, price)


@pytest.mark.parametrize("tax", [-0.1, math.nan, math.inf])
def test_invalid_tax_rejected(tax: float) -> None:
    with pytest.raises(ValueError):
        craft_cost(Craft("c", ()), buy_tax=tax)
