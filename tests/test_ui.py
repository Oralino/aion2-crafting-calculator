"""Smoke tests for the main window, run offscreen (no visible window)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator  # noqa: E402
from dataclasses import replace  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from aion2calc.app import RECIPES  # noqa: E402
from aion2calc.data.prices import PriceStore  # noqa: E402
from aion2calc.data.recipes import Catalog, searchable_recipes  # noqa: E402
from aion2calc.ocr.market import MarketReading, MarketRow  # noqa: E402
from aion2calc.session import Settings, Source  # noqa: E402
from aion2calc.ui import theme  # noqa: E402
from aion2calc.ui.main_window import MainWindow  # noqa: E402
from aion2calc.ui.settings_store import load_settings, save_settings  # noqa: E402
from aion2calc.ui.tier_block import COST, INCL, MaterialModel, TierBlock  # noqa: E402

STAR_DRAGON_LORD_NECKLACE = 310130019


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return Catalog.load(RECIPES)


@pytest.fixture
def window(catalog: Catalog, monkeypatch: pytest.MonkeyPatch) -> Iterator[MainWindow]:
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    theme.apply(app)
    # Never write the user's real settings from tests.
    monkeypatch.setattr("aion2calc.ui.main_window.save_settings", lambda settings: None)
    win = MainWindow(catalog, Settings(), PriceStore(":memory:"))
    win.open_recipe(STAR_DRAGON_LORD_NECKLACE)
    yield win
    win.close()
    win.deleteLater()
    app.processEvents()


def row_of(model: MaterialModel, text: str) -> int:
    return next(r for r in range(model.rowCount()) if text in model.row(model.index(r, 0)).name)


def top(win: MainWindow) -> TierBlock:
    return win.blocks[-1]


def test_search_lists_global_recipes_once(catalog: Catalog) -> None:
    entries = searchable_recipes(catalog)
    assert entries["Star Dragon Lord Necklace · Unique"] == STAR_DRAGON_LORD_NECKLACE
    assert all(not catalog.recipes[i].kr_tw_only for i in entries.values())
    # Faction copies (two Ruby Necklace ids) appear once.
    assert sum(1 for text in entries if text.startswith("Ruby Necklace ·")) == 1


def test_open_recipe_builds_one_block_per_tier(window: MainWindow) -> None:
    assert len(window.blocks) == 4
    assert window.summary._total.text() == "0"  # no prices yet


def test_typing_a_price_updates_the_total(window: MainWindow) -> None:
    model = top(window).model
    assert model.setData(model.index(row_of(model, "Wrathful"), COST), "370,000")
    # 6 × 370,000 per craft; 1 attempt at an unset (100%) chance; + 10% buy tax.
    assert window.summary._total.text() == "2,442,000"


def test_rejected_price_reports_and_keeps_old_value(window: MainWindow) -> None:
    model = top(window).model
    index = model.index(row_of(model, "Wrathful"), COST)
    messages: list[str] = []
    model.rejected.connect(messages.append)
    assert not model.setData(index, "12k")
    assert messages and "isn't a Kinah amount" in messages[0]
    assert model.row(index).source is Source.MISSING


def test_splendent_piece_can_be_valued_and_replaces_lower_tiers(window: MainWindow) -> None:
    model = top(window).model
    crafted = row_of(model, "Artisan's Splendent")
    assert model.row(model.index(crafted, 0)).source is Source.CRAFTED
    assert model.data(model.index(crafted, INCL), Qt.ItemDataRole.CheckStateRole) is None
    assert model.setData(model.index(crafted, COST), "20,000,000")
    assert model.row(model.index(crafted, 0)).source is Source.VALUED
    assert window.summary._total.text() == "22,000,000"  # the piece + 10% buy tax, nothing below
    assert not window.blocks[0]._notice.isHidden()  # lower tiers say they're not counted
    table = top(window).table
    table.setCurrentIndex(model.index(crafted, COST))
    QTest.keyClick(table, Qt.Key.Key_Delete)  # clearing brings the lower tiers back
    assert model.row(model.index(crafted, 0)).source is Source.CRAFTED
    assert window.blocks[0]._notice.isHidden()


def test_planned_crafts_change_the_tier_and_those_below(window: MainWindow) -> None:
    block = window.blocks[2]  # Artisan's tier
    block.crafts.setText("10")
    block.crafts.editingFinished.emit()
    assert window.session is not None
    assert window.session.tiers[2].crafts == 10
    cost = window.session.cost()
    assert cost.tiers[2].attempts == 10
    assert cost.tiers[1].attempts == pytest.approx(40)  # 10 pieces / 25%, chance 100%
    block.crafts.setText("lots")
    block.crafts.editingFinished.emit()
    assert block.crafts.property("invalid") is True
    block.crafts.setText("")
    block.crafts.editingFinished.emit()
    assert window.session.tiers[2].crafts is None
    assert block.crafts.placeholderText() == "4.0"  # back to what the chain needs


def test_keyboard_space_toggles_and_delete_clears(window: MainWindow) -> None:
    block = top(window)
    model, table = block.model, block.table
    row = row_of(model, "Wrathful")
    model.setData(model.index(row, COST), "370,000")
    table.setCurrentIndex(model.index(row, COST))
    QTest.keyClick(table, Qt.Key.Key_Space)
    assert model.row(model.index(row, 0)).excluded
    assert window.summary._total.text() == "0"
    QTest.keyClick(table, Qt.Key.Key_Space)
    QTest.keyClick(table, Qt.Key.Key_Delete)
    assert model.row(model.index(row, 0)).source is Source.MISSING


def test_invalid_rate_is_flagged_and_reported(window: MainWindow) -> None:
    block = window.blocks[0]
    block.chance.setText("150")
    block.chance.editingFinished.emit()
    assert block.chance.property("invalid") is True
    assert "percentage" in window._status.text()
    block.chance.setText("93.1")
    block.chance.editingFinished.emit()
    assert block.chance.property("invalid") is False
    assert window._status.text() == "Ready"  # the accepted edit clears the error
    assert window.session is not None
    assert window.session.tiers[0].chance == pytest.approx(0.931)


def test_reopening_keeps_prices_and_replaces_blocks(window: MainWindow) -> None:
    model = top(window).model
    model.setData(model.index(row_of(model, "Wrathful"), COST), "370,000")
    old_blocks = list(window.blocks)
    window.open_recipe(STAR_DRAGON_LORD_NECKLACE)  # same recipe: same session
    assert window.session is not None and window.session.prices
    assert all(block.parent() is None for block in old_blocks)
    assert len(window.blocks) == 4


def test_profit_and_loss(window: MainWindow) -> None:
    model = top(window).model
    model.setData(model.index(row_of(model, "Wrathful"), COST), "370,000")
    window.summary.sell_field.setText("10,000,000")
    window.summary.sell_field.editingFinished.emit()
    assert window.summary._profit_label.text() == "Profit"
    assert window.summary._profit.property("tone") == "positive"
    window.summary.sell_field.setText("1,000")
    window.summary.sell_field.editingFinished.emit()
    assert window.summary._profit_label.text() == "Loss"
    assert window.summary._profit.text().startswith("−")


def test_settings_store_ignores_bad_values(tmp_path: Path) -> None:
    stored = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    stored.setValue("tax/buy", "lots")
    stored.setValue("tax/sell", 1.5)
    assert load_settings(stored) == Settings()
    save_settings(Settings(buy_tax=0.05, sell_tax=0.0), stored)
    assert load_settings(stored) == Settings(buy_tax=0.05, sell_tax=0.0)


def test_bundled_fonts_load(window: MainWindow) -> None:
    families = theme.load_fonts()
    assert "Inter" in families
    assert "JetBrains Mono" in families


def test_top_tier_combo_shows_and_feeds_the_expected_sale(window: MainWindow) -> None:
    assert top(window).has_combo  # Star Dragon Lord has a Splendent version
    summary = window.summary
    assert not summary.combo_sell_field.isHidden()
    summary.sell_field.setText("10,000,000")
    summary.sell_field.editingFinished.emit()
    summary.combo_sell_field.setText("30,000,000")
    summary.combo_sell_field.editingFinished.emit()
    # 75% × 10M + 25% × 30M = 15M expected; minus 10% sell tax = 13.5M; no costs entered.
    assert summary._expected.text() == "15,000,000"
    assert summary._profit.text() == "+13,500,000"


def test_recipe_without_splendent_hides_its_price(window: MainWindow, catalog: Catalog) -> None:
    window.summary.combo_sell_field.setText("30,000,000")
    window.summary.combo_sell_field.editingFinished.emit()
    no_combo = next(
        i for i in searchable_recipes(catalog).values() if catalog.recipes[i].combo_item_id is None
    )
    window.open_recipe(no_combo)
    assert window.summary.combo_sell_field.isHidden()
    assert window.summary.combo_sell_field.text() == ""
    assert window.session is not None and window.session.combo_sell_price is None


def test_bad_splendent_price_names_the_field(window: MainWindow) -> None:
    window.summary.combo_sell_field.setText("lots")
    window.summary.combo_sell_field.editingFinished.emit()
    assert window.summary.combo_sell_field.property("invalid") is True
    assert window._status.text().startswith("Splendent price")


def wrathful_ids(catalog: Catalog) -> tuple[int, ...]:
    return tuple(i for i, item in catalog.items.items() if item.name == "Wrathful Mind")


def test_capture_prices_flow_into_the_calculator(window: MainWindow, catalog: Catalog) -> None:
    row = MarketRow("Wrathful Mind", "Wrathful Mind", wrathful_ids(catalog), True, 39, 999_990)
    window.apply_reading(MarketReading((row,)))
    model = top(window).model
    wrathful = model.row(model.index(row_of(model, "Wrathful"), 0))
    assert (wrathful.unit_price, wrathful.source) == (999_990, Source.OCR)
    assert window._status.text() == "Captured 1 price: Wrathful Mind"
    # A manual price still wins, and is saved.
    model.setData(model.index(row_of(model, "Wrathful"), COST), "900,000")
    assert model.row(model.index(row_of(model, "Wrathful"), 0)).source is Source.MANUAL
    assert window._store.manual_prices()[wrathful.item_id] == 900_000
    # A new capture is newer, so it replaces the typed price.
    window.apply_reading(MarketReading((replace(row, price=950_000),)))
    again = model.row(model.index(row_of(model, "Wrathful"), 0))
    assert (again.unit_price, again.source) == (950_000, Source.OCR)
    assert wrathful.item_id not in window._store.manual_prices()


def test_capture_problems_are_reported(window: MainWindow) -> None:
    window.apply_reading(MarketReading((), "market list not found"))
    assert window._status.text() == "Capture failed: market list not found"
    window.apply_reading(MarketReading((MarketRow("Ruby", "Ruby", (1,), True, None, None),)))
    assert window._status.text().startswith("! No prices captured")


def test_market_price_of_the_finished_item_fills_the_sell_price(
    window: MainWindow, catalog: Catalog
) -> None:
    ids = tuple(i for i, item in catalog.items.items() if item.name == "Star Dragon Lord Necklace")
    row = MarketRow(
        "Star Dragon Lord Necklace", "Star Dragon Lord Necklace", ids, True, 2, 40_000_000
    )
    window.apply_reading(MarketReading((row,)))
    assert window.summary.sell_field.placeholderText() == "40,000,000 (market)"
    assert window.summary._profit.text() != "—"  # a profit is shown without typing anything


def test_a_capture_replaces_the_typed_sell_price(window: MainWindow, catalog: Catalog) -> None:
    ids = tuple(i for i, item in catalog.items.items() if item.name == "Star Dragon Lord Necklace")
    window.summary.sell_field.setText("10,000,000")
    window.summary.sell_field.editingFinished.emit()
    row = MarketRow("Ruby", "Ruby", (1,), True, 5, 100)  # another item leaves it alone
    window.apply_reading(MarketReading((row,)))
    assert window.session is not None and window.session.sell_price == 10_000_000
    row = MarketRow(
        "Star Dragon Lord Necklace", "Star Dragon Lord Necklace", ids, True, 2, 40_000_000
    )
    window.apply_reading(MarketReading((row,)))
    assert window.session.sell_price is None
    assert window.session.effective_sell_price() == 40_000_000
    assert window.summary.sell_field.text() == ""


def test_search_dropdown_matches_words_in_any_order(window: MainWindow) -> None:
    from aion2calc.ui.recipe_search import matching

    names = ["Ruby Necklace · Common", "Star Dragon Lord Necklace · Unique", "Ruby Ring · Common"]
    assert matching(names, "neck ruby") == ["Ruby Necklace · Common"]
    assert matching(names, "ruby") == ["Ruby Necklace · Common", "Ruby Ring · Common"]
    assert matching(names, "  ") == []
    search = window.search
    search.setText("star neck")
    search.textEdited.emit("star neck")
    shown = search._model.stringList()
    assert "Star Dragon Lord Necklace · Unique" in shown
    opened: list[int] = []
    search.chosen.connect(opened.append)
    search.choose("Star Dragon Lord Necklace · Unique")
    assert opened == [STAR_DRAGON_LORD_NECKLACE]


def test_approximate_names_are_reported_not_saved(window: MainWindow, catalog: Catalog) -> None:
    row = MarketRow("Wrathfull Mind", "Wrathful Mind", wrathful_ids(catalog), False, 39, 1)
    window.apply_reading(MarketReading((row,)))
    assert window._status.text() == "! Not saved, name not recognised exactly: Wrathfull Mind"
    assert window._store.latest_ocr() == {}


def test_unexpected_errors_are_logged_and_shown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import aion2calc.app as app

    shown: list[str] = []
    monkeypatch.setattr(app, "default_path", lambda: tmp_path / "prices.sqlite3")
    monkeypatch.setattr(QMessageBox, "critical", lambda _p, _t, text: shown.append(text))
    try:
        raise KeyError("boom")
    except KeyError as error:
        app._report_error(KeyError, error, error.__traceback__)
    assert "KeyError: 'boom'" in (tmp_path / "error.log").read_text(encoding="utf-8")
    assert shown and "error.log" in shown[0]
