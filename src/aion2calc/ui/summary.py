"""Right-hand summary: craft total, tax, total cost, warnings, sell prices and (expected) profit."""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from aion2calc.session import CraftSession
from aion2calc.ui.format import DASH, MINUS, kinah, parse_kinah, signed_kinah


def _label(text: str, role: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    return label


def _restyle(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _divider() -> QFrame:
    line = QFrame()
    line.setProperty("role", "divider")
    return line


class _PriceField(QLineEdit):
    """A Kinah input that validates on Enter/focus-out and writes through a session setter."""

    def __init__(self, accessible_name: str, tip: str) -> None:
        super().__init__()
        self.setProperty("numeric", True)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setPlaceholderText("Kinah")
        self.setToolTip(tip)
        self.setAccessibleName(accessible_name)

    def show_price(self, price: int | None) -> None:
        self.setText("" if price is None else f"{price:,}")
        self.set_invalid(False)

    def set_invalid(self, invalid: bool) -> None:
        self.setProperty("invalid", invalid)
        _restyle(self)


class SummaryPanel(QWidget):
    changed = Signal()
    message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("summary")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFixedWidth(280)
        self._session: CraftSession | None = None

        self._craft_total = _label(DASH, "num")
        self._buy_tax_label = _label("Buy tax", "secondary")
        self._buy_tax = _label(DASH, "num")
        self._total = _label(DASH, "display")
        self._warnings = _label("", "warning")
        self._warnings.setWordWrap(True)
        self.sell_field = _PriceField(
            "Sell price in Kinah", "What the finished item sells for on the market"
        )
        self.combo_sell_field = _PriceField(
            "Splendent sell price in Kinah",
            "What the Splendent (combo) version of the finished item sells for",
        )
        self.sell_field.editingFinished.connect(
            lambda: self._price_edited(self.sell_field, "Sell price", CraftSession.set_sell_price)
        )
        self.combo_sell_field.editingFinished.connect(
            lambda: self._price_edited(
                self.combo_sell_field, "Splendent price", CraftSession.set_combo_sell_price
            )
        )
        self._combo_sell_label = _label("Splendent price", "secondary")
        self._expected_label = _label("Sale", "secondary")
        self._expected = _label(DASH, "num")
        self._sell_tax_label = _label("Sell tax", "secondary")
        self._sell_tax = _label(DASH, "num")
        self._net = _label(DASH, "num")
        self._profit_label = _label("Profit", "secondary")
        self._profit = _label(DASH, "display")
        self._profit_hint = _label("Enter a sell price", "caption")
        self._profit_hint.setWordWrap(True)

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(8)
        rows: list[tuple[QWidget, QWidget | None]] = [
            (_label("Craft total", "secondary"), self._craft_total),
            (self._buy_tax_label, self._buy_tax),
            (_label("Total cost", "title"), self._total),
            (self._warnings, None),
            (_divider(), None),
            (_label("Sell price", "secondary"), self.sell_field),
            (self._combo_sell_label, self.combo_sell_field),
            (self._expected_label, self._expected),
            (self._sell_tax_label, self._sell_tax),
            (_label("Net sale", "secondary"), self._net),
            (self._profit_label, self._profit),
            (self._profit_hint, None),
        ]
        for row, (left, right) in enumerate(rows):
            if right is None:
                grid.addWidget(left, row, 0, 1, 2)
            else:
                grid.addWidget(left, row, 0)
                grid.addWidget(right, row, 1, Qt.AlignmentFlag.AlignRight)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(_label("Summary", "title"))
        layout.addSpacing(8)
        layout.addLayout(grid)
        layout.addStretch(1)
        self._show_combo(False)

    def focus_chain(self) -> list[QWidget]:
        return [self.sell_field, *([self.combo_sell_field] if self._has_combo() else [])]

    def _has_combo(self) -> bool:
        return self._session is not None and self._session.final_combo_item is not None

    def _show_combo(self, visible: bool) -> None:
        for widget in (self._combo_sell_label, self.combo_sell_field):
            widget.setVisible(visible)

    def set_session(self, session: CraftSession | None) -> None:
        self._session = session
        self.sell_field.show_price(None if session is None else session.sell_price)
        self.combo_sell_field.show_price(None if session is None else session.combo_sell_price)
        self._show_combo(self._has_combo())
        self.refresh()

    def _price_edited(
        self,
        field: _PriceField,
        name: str,
        setter: Callable[[CraftSession, int | None], None],
    ) -> None:
        if self._session is None:
            return
        before = (self._session.sell_price, self._session.combo_sell_price)
        try:
            price = parse_kinah(field.text())
            setter(self._session, price)
        except ValueError:
            field.set_invalid(True)
            self.message.emit(f"{name} must be a Kinah amount, e.g. 2,500,000")
            return
        field.show_price(price)
        if (self._session.sell_price, self._session.combo_sell_price) != before:
            self.changed.emit()

    def refresh(self) -> None:
        session = self._session
        if session is None:
            for value in (
                self._craft_total,
                self._buy_tax,
                self._total,
                self._expected,
                self._sell_tax,
                self._net,
                self._profit,
            ):
                value.setText(DASH)
            self._warnings.setText("")
            self._warnings.setVisible(False)
            return
        settings = session.settings
        cost = session.cost()
        self._buy_tax_label.setText(f"Buy tax ({settings.buy_tax * 100:g}%)")
        self._sell_tax_label.setText(f"Sell tax ({settings.sell_tax * 100:g}%)")
        self._craft_total.setText(kinah(cost.subtotal))
        self._buy_tax.setText(signed_kinah(cost.tax))
        self._total.setText(kinah(cost.total))
        warnings = session.warnings()
        self._warnings.setText("\n".join(f"! {w}" for w in warnings))
        self._warnings.setVisible(bool(warnings))

        combo = self._has_combo()
        rate = session.tiers[-1].combo_rate
        self._expected_label.setText("Expected sale" if combo else "Sale")
        self._expected_label.setToolTip(
            f"{100 - rate * 100:g}% at the sell price, {rate * 100:g}% at the Splendent price "
            "(the top tier's combo chance)"
            if combo
            else ""
        )
        sale = session.sale()
        if sale is None:
            for value in (self._expected, self._sell_tax, self._net, self._profit):
                value.setText(DASH)
            self._profit_label.setText("Profit")
            self._profit.setProperty("tone", "muted")
            self._profit_hint.setText("Enter a sell price")
            self._profit_hint.setVisible(True)
        else:
            self._expected.setText(kinah(sale.gross))
            self._sell_tax.setText(f"{MINUS}{kinah(sale.tax)}" if round(sale.tax) else "0")
            self._net.setText(kinah(sale.net))
            loss = round(sale.profit) < 0
            self._profit_label.setText("Loss" if loss else "Profit")
            self._profit.setText(signed_kinah(sale.profit))
            self._profit.setProperty("tone", "danger" if loss else "positive")
            self._profit_hint.setText("Average over many crafts; one craft gives one or the other.")
            self._profit_hint.setVisible(combo)
        _restyle(self._profit)
