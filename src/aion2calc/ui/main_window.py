"""Main window: header (recipe search, tabs), calculator page, summary panel, status bar."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QStatusBar,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from aion2calc.data.prices import PriceStore
from aion2calc.data.recipes import Catalog
from aion2calc.ocr.market import MarketReading
from aion2calc.session import CraftSession, Settings
from aion2calc.ui.recipe_search import RecipeSearch
from aion2calc.ui.settings_page import SettingsPage
from aion2calc.ui.settings_store import save_settings
from aion2calc.ui.summary import SummaryPanel
from aion2calc.ui.tier_block import TierBlock

TABS = ["Calculator", "Prices", "Settings"]


def _label(text: str, role: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    return label


class MainWindow(QMainWindow):
    def __init__(self, catalog: Catalog, settings: Settings, store: PriceStore) -> None:
        super().__init__()
        self.setWindowTitle("Aion2 Crafting Calculator")
        self.setMinimumSize(960, 640)
        self.resize(1280, 800)
        self._catalog = catalog
        self._settings = settings
        self._store = store
        self.session: CraftSession | None = None
        self.blocks: list[TierBlock] = []

        self.search = RecipeSearch(catalog)
        self.search.chosen.connect(self.open_recipe)
        self.search.not_found.connect(self.show_message)
        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setExpanding(False)
        for name in TABS:
            self.tabs.addTab(name)
        header = QWidget()
        header.setObjectName("header")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        header.setFixedHeight(56)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.addWidget(self.search)
        header_layout.addSpacing(16)
        header_layout.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignBottom)
        header_layout.addStretch(1)

        self.summary = SummaryPanel()
        self.summary.changed.connect(self.recalculate)
        self.summary.message.connect(self.show_message)
        self._tiers = QWidget()
        self._tiers_layout = QVBoxLayout(self._tiers)
        self._tiers_layout.setContentsMargins(16, 16, 16, 16)
        self._tiers_layout.setSpacing(16)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._tiers)
        calculator = QWidget()
        calculator_layout = QHBoxLayout(calculator)
        calculator_layout.setContentsMargins(0, 0, 0, 0)
        calculator_layout.setSpacing(0)
        calculator_layout.addWidget(scroll, 1)
        calculator_layout.addWidget(self.summary)

        prices = QWidget()
        prices_layout = QVBoxLayout(prices)
        prices_layout.setContentsMargins(16, 16, 16, 16)
        prices_layout.addWidget(
            _label(
                "Price history arrives with auction house capture. For now, type prices into "
                "the Cost per column on the Calculator tab.",
                "secondary",
            )
        )
        prices_layout.addStretch(1)

        settings_page = SettingsPage(settings, save_settings)
        settings_page.changed.connect(self.recalculate)
        settings_page.message.connect(self.show_message)

        self.pages = QStackedWidget()
        for page in (calculator, prices, settings_page):
            self.pages.addWidget(page)
        self.tabs.currentChanged.connect(self.pages.setCurrentIndex)

        root = QWidget()
        root.setObjectName("app")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(header)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self._capture_label = _label("Capture: not set up", "caption")
        status.addWidget(self._capture_label)
        self._status = _label("Ready", "caption")
        self._status.setProperty("tone", "muted")
        status.addWidget(self._status, 1)
        self.setStatusBar(status)

        for keys in ("Ctrl+K", "Ctrl+F"):
            QShortcut(QKeySequence(keys), self, self._focus_search)
        for number in range(len(TABS)):
            QShortcut(
                QKeySequence(f"Ctrl+{number + 1}"),
                self,
                lambda index=number: self.tabs.setCurrentIndex(index),
            )
        self._show_empty()

    def _focus_search(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.search.setFocus()
        self.search.selectAll()

    def _clear_tiers(self) -> None:
        while (item := self._tiers_layout.takeAt(0)) is not None:
            if (widget := item.widget()) is not None:
                widget.hide()  # deleteLater waits for the event loop; don't leave it on screen
                widget.setParent(None)
                widget.deleteLater()
        self.blocks = []

    def _show_empty(self) -> None:
        self._clear_tiers()
        self._tiers_layout.addWidget(_label("Search a recipe to start (Ctrl+K).", "secondary"))
        self._tiers_layout.addStretch(1)
        self.summary.set_session(None)

    def open_recipe(self, item_id: int) -> None:
        old = self.session
        self._clear_tiers()  # before replacing the session, so old blocks can't recalculate it
        if old is not None and old.final_item == item_id:
            self.session = old  # re-picking the open recipe keeps every input
        else:
            self.session = CraftSession(
                self._catalog,
                item_id,
                self._settings,
                prices=self._store.manual_prices(),
                market=self._store.latest_ocr(),
            )
            self.session.on_manual_price = self._store.set_manual
        self._tiers_layout.addWidget(_label(self.session.name(item_id), "heading"))
        for index in range(len(self.session.tiers)):
            block = TierBlock(self.session, index)
            block.changed.connect(self.recalculate)
            block.message.connect(self.show_message)
            self.blocks.append(block)
            self._tiers_layout.addWidget(block)
        self._tiers_layout.addStretch(1)
        self.summary.set_session(self.session)
        self.recalculate()
        self._set_tab_order()
        self.tabs.setCurrentIndex(0)
        self.blocks[0].chance.setFocus()

    def _set_tab_order(self) -> None:
        """Reading order (DESIGN.md): search, tabs, each tier's inputs and table, then summary."""
        chain: list[QWidget] = [self.search, self.tabs]
        for block in self.blocks:
            chain += block.focus_chain()
        chain += self.summary.focus_chain()
        for first, second in zip(chain, chain[1:], strict=False):
            QWidget.setTabOrder(first, second)

    def recalculate(self) -> None:
        """Called after every accepted edit, so it also clears an earlier error message."""
        self._set_status("Ready", "muted")
        if self.session is None:
            return
        cost = self.session.cost()
        for block, tier_cost in zip(self.blocks, cost.tiers, strict=True):
            block.refresh(tier_cost)
        self.summary.refresh()

    def show_message(self, text: str) -> None:
        self._set_status(text, "danger")

    def set_capture_label(self, text: str) -> None:
        self._capture_label.setText(text)

    def capture_started(self) -> None:
        self._set_status("Reading listings…", "")

    def apply_reading(self, reading: MarketReading, when: datetime | None = None) -> None:
        """Store a capture's prices, refresh the calculator and report what was read."""
        if reading.problem:
            self.show_message(f"Capture failed: {reading.problem}")
            return
        priced = reading.priced
        approximate = reading.approximate
        unsaved = ""
        if approximate:
            names = ", ".join(r.text for r in approximate[:2])
            more = f" +{len(approximate) - 2} more" if len(approximate) > 2 else ""
            unsaved = f"! Not saved, name not recognised exactly: {names}{more}"
        if not priced:
            if approximate:
                detail = unsaved
            elif reading.rows:
                count = len(reading.rows)
                detail = f"! No prices captured: {count} items had no listings or no clear price"
            else:
                detail = "! No prices captured: no known items in the list"
            self._set_status(detail, "warning")
            return
        self._store.record_ocr(
            [(r.item_ids, r.price, r.listings) for r in priced if r.price is not None], at=when
        )
        if self.session is not None:
            self.session.market = self._store.latest_ocr()
            self.session.prices = self._store.manual_prices()  # the capture replaced typed ones
            captured = {item_id for row in priced for item_id in row.item_ids}
            if self.session.clear_captured_sell_prices(captured):
                self.summary.set_session(self.session)  # empty the replaced sell price fields
            self.recalculate()
        names = ", ".join(r.name or r.text for r in priced[:3])
        more = f" +{len(priced) - 3} more" if len(priced) > 3 else ""
        noun = "price" if len(priced) == 1 else "prices"
        summary = f"Captured {len(priced)} {noun}: {names}{more}"
        if unsaved:
            self._set_status(f"{summary} · {unsaved}", "warning")
        else:
            self._set_status(summary, "positive")

    def _set_status(self, text: str, tone: str) -> None:
        self._status.setText(text)
        self._status.setProperty("tone", tone)
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)
