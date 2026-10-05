import math
from dataclasses import replace

import pytest

from aion2calc.calc import Craft, Material, Tier, craft_cost

# The owner's Google Sheet, "Accessories" tab. Expected values are the sheet's own results.
ACCESSORIES = Craft(
    "Accessory",
    (
        Tier(
            "Grey",
            64,
            (
                Material("Diamond Decoration", 1, None),
                Material("Refining stone", 3, 4_000),
                Material("Odyle", 1, None),
            ),
            chance=0.93121326,
        ),
        Tier(
            "Green",
            16,
            (
                Material("Expert's Refining stone", 3, 45_000),
                Material("Fine Diamond Gemstone", 3, 3_000),
                Material("Fine Odyle", 2, 3_000),
            ),
            chance=0.94633946,
        ),
        Tier(
            "Blue",
            4,
            (
                Material("Artisan's Refining stone", 3, 300_000),
                Material("Pure Diamond Gemstone", 4, 50_000),
                Material("Pure Odyle", 2, 85_000),
            ),
            chance=0.96837241,
        ),
        Tier(
            "Legendary",
            1,
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


def test_accessories_matches_sheet() -> None:
    result = craft_cost(ACCESSORIES, buy_tax=0.1)
    expected_tiers = (824_730.5241, 2_536_087.843, 5_245_915.67, 2_826_506.724)
    assert result.tier_costs == pytest.approx(expected_tiers, abs=0.01)
    assert result.subtotal == pytest.approx(11_433_240.76, abs=0.01)
    assert result.total == pytest.approx(12_576_564.84, abs=0.01)


def test_needed_crafts() -> None:
    assert Tier("t", 64, (), chance=0.5).needed == 128
    assert Tier("t", 64, (), chance=1.0).needed == 64
    assert Tier("t", 64, ()).needed == 64
    assert Tier("t", 0, (Material("m", 1, 100),)).cost == 0


def test_buy_tax_on_round_numbers() -> None:
    result = craft_cost(Craft("c", (Tier("t", 2, (Material("m", 5, 100),)),)), buy_tax=0.1)
    assert result.subtotal == 1_000
    assert result.tax == pytest.approx(100)
    assert result.total == pytest.approx(1_100)


def test_empty_craft_costs_nothing() -> None:
    assert craft_cost(Craft("c", ())).total == 0


def test_exclusion_toggle_changes_cost() -> None:
    excluded = Material("m", 2, 100, excluded=True)
    tier = Tier("t", 1, (excluded,))
    assert tier.cost_per_craft == 0
    assert replace(tier, materials=(replace(excluded, excluded=False),)).cost_per_craft == 200


def test_excluded_and_unpriced_materials_cost_nothing() -> None:
    tier = Tier(
        "t",
        1,
        (
            Material("priced", 2, 100),
            Material("excluded", 5, 1_000, excluded=True),
            Material("no price", 3, None),
        ),
    )
    assert tier.cost_per_craft == 200


def test_no_tax_by_default() -> None:
    result = craft_cost(Craft("c", (Tier("t", 2, (Material("m", 1, 50),)),)))
    assert result.tax == 0
    assert result.total == 100


@pytest.mark.parametrize("chance", [0.0, -0.1, 1.5, math.nan])
def test_invalid_chance_rejected(chance: float) -> None:
    with pytest.raises(ValueError):
        Tier("t", 1, (), chance=chance)


def test_negative_target_rejected() -> None:
    with pytest.raises(ValueError):
        Tier("t", -1, ())


@pytest.mark.parametrize(("qty", "price"), [(-1, 100), (1, -100)])
def test_negative_material_values_rejected(qty: int, price: int) -> None:
    with pytest.raises(ValueError):
        Material("m", qty, price)


@pytest.mark.parametrize("tax", [-0.1, math.nan, math.inf])
def test_invalid_tax_rejected(tax: float) -> None:
    with pytest.raises(ValueError):
        craft_cost(Craft("c", ()), buy_tax=tax)
