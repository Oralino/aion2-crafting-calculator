from datetime import UTC, datetime

import pytest

from aion2calc.data.aion2hub import Component, RecipePage
from aion2calc.data.prices import Observation, PriceSource
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


def seen(item_id: int, price: int) -> Observation:
    return Observation(item_id, price, 10, datetime(2026, 10, 5, tzinfo=UTC), PriceSource.OCR)


def test_manual_beats_market_beats_missing() -> None:
    s = CraftSession(CATALOG, 20, market={1: seen(1, 4_000), 3: seen(3, 95_000)})
    stone, odyle = s.rows(0)
    assert (stone.unit_price, stone.source) == (4_000, Source.OCR)
    assert stone.observed_at == datetime(2026, 10, 5, tzinfo=UTC)
    assert odyle.source is Source.MISSING
    s.set_price(1, 3_500)
    assert (s.rows(0)[0].unit_price, s.rows(0)[0].source) == (3_500, Source.MANUAL)
    s.set_price(1, None)  # clearing falls back to the market
    assert s.rows(0)[0].source is Source.OCR


def test_manual_price_changes_are_reported() -> None:
    s = session()
    calls: list[tuple[int, int | None]] = []
    s.on_manual_price = lambda item_id, price: calls.append((item_id, price))
    s.set_price(1, 10)
    s.set_price(1, None)
    assert calls == [(1, 10), (1, None)]


def test_market_price_of_the_finished_item_is_the_default_sell_price() -> None:
    catalog, _ = build_catalog(
        [
            page(10, "Ruby Necklace", "Common", STONE),
            page(11, "Splendent Ruby Necklace", "Rare", STONE),
        ]
    )
    s = CraftSession(catalog, 10, market={10: seen(10, 1_000), 11: seen(11, 5_000)})
    s.settings.sell_tax = 0
    assert gross(s) == 0.75 * 1_000 + 0.25 * 5_000
    s.set_sell_price(2_000)  # a typed price wins
    assert gross(s) == 0.75 * 2_000 + 0.25 * 5_000


def test_planned_crafts_drive_the_cost() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.set_price(3, 1_000)  # Expert's Refining Stone ×4 per craft in tier 2
    s.set_crafts(1, 5)
    assert s.cost().tiers[1].attempts == 5
    assert s.cost().tiers[1].cost == 20_000
    assert s.cost().tiers[0].attempts == 20  # 5 Splendent pieces / 25% combo
    s.set_crafts(1, None)
    assert s.cost().tiers[1].attempts == 1
    with pytest.raises(ValueError):
        s.set_crafts(0, -1)


def test_valued_splendent_piece_replaces_the_tiers_below() -> None:
    s = session()
    s.settings.buy_tax = 0
    s.set_price(1, 100)  # tier 1 material
    s.set_price(3, 1_000)  # tier 2 material
    assert s.has_crafted_input(1) and not s.has_crafted_input(0)
    s.set_crafted_value(1, 50_000)
    row = s.rows(1)[0]
    assert (row.source, row.unit_price) == (Source.VALUED, 50_000)
    cost = s.cost()
    assert not cost.tiers[0].counted
    assert cost.total == 50_000 + 4 * 1_000  # one attempt: the piece plus its materials
    assert not s.counted(0) and s.counted(1)
    assert "no price" not in " ".join(s.warnings())  # tier 1's missing Odyle no longer matters
    s.set_crafted_value(1, None)
    assert s.rows(1)[0].source is Source.CRAFTED
    assert s.cost().tiers[0].counted
    with pytest.raises(ValueError):
        s.set_crafted_value(0, 10)  # the base tier has no Splendent input


def test_planned_top_crafts_sell_the_items_they_make() -> None:
    s = session()
    s.settings.buy_tax = s.settings.sell_tax = 0
    s.set_chance(1, 0.5)
    s.set_crafts(1, 4)  # 4 crafts at 50%: 2 items to sell
    s.set_sell_price(1_000)
    assert gross(s) == 2_000


def test_planned_crafts_too_low_for_the_tier_above_are_flagged() -> None:
    s = session()
    s.set_crafts(1, 5)  # needs 5 Splendent pieces: 20 crafts below at 100% and 25% combo
    s.set_crafts(0, 8)  # makes 2
    assert s.warnings()[-1] == "Ruby Necklace makes fewer Splendent pieces than the tier above uses"
    s.set_crafts(0, 20)
    assert not any("fewer Splendent" in w for w in s.warnings())
