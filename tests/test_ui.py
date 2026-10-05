"""Smoke tests for the main window, run offscreen (no visible window)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from aion2calc.app import RECIPES  # noqa: E402
from aion2calc.data.recipes import Catalog, searchable_recipes  # noqa: E402
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
    win = MainWindow(catalog, Settings())
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


def test_crafted_combo_item_cannot_be_edited_or_excluded(window: MainWindow) -> None:
    model = top(window).model
    crafted = row_of(model, "Artisan's Splendent")
    assert model.row(model.index(crafted, 0)).source is Source.CRAFTED
    assert not model.flags(model.index(crafted, COST)) & Qt.ItemFlag.ItemIsEditable
    assert not model.setData(model.index(crafted, COST), "100")
    assert model.data(model.index(crafted, INCL), Qt.ItemDataRole.CheckStateRole) is None


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
