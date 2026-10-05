"""Right-hand summary: craft total, tax, total cost, warnings, sell price and profit."""

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
        self._sell = QLineEdit()
        self._sell.setProperty("numeric", True)
        self._sell.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._sell.setPlaceholderText("Kinah")
        self._sell.setToolTip("What the finished item sells for on the market")
        self._sell.setAccessibleName("Sell price in Kinah")
        self._sell.editingFinished.connect(self._sell_edited)
        self._sell_tax_label = _label("Sell tax", "secondary")
        self._sell_tax = _label(DASH, "num")
        self._net = _label(DASH, "num")
        self._profit_label = _label("Profit", "secondary")
        self._profit = _label(DASH, "display")
        self._profit_hint = _label("Enter a sell price", "caption")

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(8)
        rows: list[tuple[QWidget, QWidget | None]] = [
            (_label("Craft total", "secondary"), self._craft_total),
            (self._buy_tax_label, self._buy_tax),
            (_label("Total cost", "title"), self._total),
            (self._warnings, None),
            (_divider(), None),
            (_label("Sell price", "secondary"), self._sell),
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

    def set_session(self, session: CraftSession | None) -> None:
        self._session = session
        self._sell.setText(
            "" if session is None or session.sell_price is None else f"{session.sell_price:,}"
        )
        self.refresh()

    def _sell_edited(self) -> None:
        if self._session is None:
            return
        try:
            price = parse_kinah(self._sell.text())
            if price != self._session.sell_price:
                self._session.set_sell_price(price)
                changed = True
            else:
                changed = False
        except ValueError:
            self._sell.setProperty("invalid", True)
            _restyle(self._sell)
            self.message.emit("Sell price must be a Kinah amount, e.g. 2,500,000")
            return
        self._sell.setProperty("invalid", False)
        _restyle(self._sell)
        if price is not None:
            self._sell.setText(f"{price:,}")
        if changed:
            self.changed.emit()

    @property
    def sell_field(self) -> QLineEdit:
        return self._sell

    def refresh(self) -> None:
        session = self._session
        if session is None:
            for value in (
                self._craft_total,
                self._buy_tax,
                self._total,
                self._sell_tax,
                self._net,
                self._profit,
            ):
                value.setText(DASH)
            self._warnings.setText("")
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

        sale = session.sale()
        if sale is None:
            self._sell_tax.setText(DASH)
            self._net.setText(DASH)
            self._profit.setText(DASH)
            self._profit_label.setText("Profit")
            self._profit.setProperty("tone", "muted")
            self._profit_hint.setVisible(True)
        else:
            self._sell_tax.setText(f"{MINUS}{kinah(sale.tax)}" if round(sale.tax) else "0")
            self._net.setText(kinah(sale.net))
            loss = round(sale.profit) < 0
            self._profit_label.setText("Loss" if loss else "Profit")
            self._profit.setText(signed_kinah(sale.profit))
            self._profit.setProperty("tone", "danger" if loss else "positive")
            self._profit_hint.setVisible(False)
        _restyle(self._profit)


def _divider() -> QFrame:
    line = QFrame()
    line.setProperty("role", "divider")
    return line
