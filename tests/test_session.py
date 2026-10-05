import pytest

from aion2calc.data.aion2hub import Component, RecipePage
from aion2calc.data.recipes import build_catalog
from aion2calc.session import CraftSession, Settings, Source

STONE = Component(1, "Refining Stone", 4)
ODYLE = Component(2, "Odyle", 1)
FINE = Component(3, "Expert's Refining Stone", 4)


def page(item_id: int, name: str, grade: str, *parts: Component) -> RecipePage:
    return RecipePage(item_id, name, grade, "Jewelcrafting", 10, parts)


CATALOG, _ = build_catalog(
    [
        page(10, "Ruby Necklace", "Common", STONE, ODYLE),
        page(11, "Splendent Ruby Necklace", "Rare", STONE, ODYLE),
        page(20, "Expert's Ruby Necklace", "Rare", Component(11, "Splendent", 1), FINE),
    ]
)


def gross(s: CraftSession) -> float:
    result = s.sale()
    assert result is not None
    return result.gross


def session() -> CraftSession:
    return CraftSession(CATALOG, 20)


def test_combo_item_from_tier_below_is_crafted_not_bought() -> None:
    rows = session().rows(1)
    assert rows[0].name == "Splendent Ruby Necklace"
    assert rows[0].source is Source.CRAFTED
    assert rows[1].source is Source.MISSING


def test_prices_are_shared_between_tiers_and_feed_the_cost() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.set_price(1, 100)  # Refining Stone, tier 1 only
    s.set_price(3, 1_000)  # Expert's Refining Stone, tier 2
    cost = s.cost()
    # Tier 2: 1 attempt × 4,000. Tier 1: 1 combo item / 0.25 = 4 attempts × 400.
    assert [t.cost for t in cost.tiers] == [1_600, 4_000]
    assert s.rows(0)[0].total == 400


def test_exclusion_and_clearing_a_price() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.set_price(3, 1_000)
    s.set_excluded(1, 3, True)
    assert s.cost().total == 0
    s.set_excluded(1, 3, False)
    s.set_price(3, None)
    assert s.rows(1)[1].source is Source.MISSING


def test_warnings_name_missing_prices_and_chances() -> None:
    s = session()
    assert s.warnings() == [
        "3 materials have no price (counted as 0)",
        "2 tiers have no craft chance (counted as 100%)",
    ]
    s.set_price(1, 1)
    s.set_price(2, 1)
    s.set_price(3, 1)
    for tier in s.tiers:
        tier.chance = 0.9
    assert s.warnings() == []


def test_sale_after_tax() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.settings.sell_tax = 0.1
    s.set_price(3, 1_000)
    assert s.sale() is None
    s.sell_price = 10_000
    sale = s.sale()
    assert sale is not None
    assert sale.net == pytest.approx(9_000)
    assert sale.profit == pytest.approx(5_000)


def test_out_of_range_inputs_rejected() -> None:
    s = session()
    for bad in (-1, 10**13):
        with pytest.raises(ValueError):
            s.set_price(1, bad)
    with pytest.raises(ValueError):
        s.set_chance(0, 0)
    with pytest.raises(ValueError):
        s.set_combo_rate(0, 1.5)
    with pytest.raises(ValueError):
        s.settings.set_sell_tax(1.0)
    with pytest.raises(ValueError):
        Settings(buy_tax=-0.1)


def test_price_on_the_crafted_item_is_ignored() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.set_price(11, 1_000_000)  # someone typed a price for the Splendent item
    assert s.rows(1)[0].source is Source.CRAFTED
    assert s.cost().total == 0


def test_exclusion_is_per_tier() -> None:
    catalog, _ = build_catalog(
        [
            page(10, "Ruby Necklace", "Common", STONE, ODYLE),
            page(11, "Splendent Ruby Necklace", "Rare", STONE, ODYLE),
            page(20, "Expert's Ruby Necklace", "Rare", Component(11, "Splendent", 1), ODYLE),
        ]
    )
    s = CraftSession(catalog, 20)
    s.set_excluded(1, ODYLE.item_id, True)  # Odyle in tier 2 only
    assert s.rows(1)[1].excluded
    assert not s.rows(0)[1].excluded


def test_prices_carry_into_a_new_session() -> None:
    s = CraftSession(CATALOG, 20, prices={1: 100})
    assert s.rows(0)[0].unit_price == 100


def test_top_tier_combo_counts_in_the_sale() -> None:
    catalog, _ = build_catalog(
        [
            page(10, "Ruby Necklace", "Common", STONE),
            page(11, "Splendent Ruby Necklace", "Rare", STONE),
        ]
    )
    s = CraftSession(catalog, 10)
    s.settings.sell_tax = 0
    assert s.final_combo_item == 11
    s.set_sell_price(1_000)
    assert s.warnings()[-1] == "No Splendent sell price (valued at the normal price)"
    assert gross(s) == 1_000
    s.set_combo_sell_price(5_000)
    s.set_combo_rate(0, 0.5)
    assert gross(s) == 3_000


def test_no_combo_version_sells_at_one_price() -> None:
    s = session()  # Expert's Ruby Necklace: no Splendent version in this catalog
    s.settings.sell_tax = 0
    s.set_sell_price(1_000)
    s.set_combo_sell_price(9_000)
    assert s.final_combo_item is None
    assert gross(s) == 1_000


def test_low_splendent_price_is_flagged_and_top_combo_leaves_cost_alone() -> None:
    catalog, _ = build_catalog(
        [
            page(10, "Ruby Necklace", "Common", STONE),
            page(11, "Splendent Ruby Necklace", "Rare", STONE),
        ]
    )
    s = CraftSession(catalog, 10)
    s.set_price(STONE.item_id, 100)
    cost_before = s.cost().total
    s.set_combo_rate(0, 0.5)
    assert s.cost().total == cost_before  # the top combo only changes the sale
    assert s.warnings() == ["1 tier has no craft chance (counted as 100%)"]  # no sell price yet
    s.set_sell_price(5_000)
    s.set_combo_sell_price(500)
    assert s.warnings()[-1] == "Splendent sell price is below the normal price; typo?"
