"""Settings tab: buy and sell tax for now. Changes apply immediately and are remembered."""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from aion2calc.session import Settings
from aion2calc.ui.format import parse_percent


class SettingsPage(QWidget):
    changed = Signal()
    message = Signal(str)

    def __init__(self, settings: Settings, save: Callable[[Settings], None]) -> None:
        super().__init__()
        self._settings = settings
        self._save = save
        self._buy = self._tax_field(settings.buy_tax, "Buy tax", "Added to bought materials")
        self._sell = self._tax_field(settings.sell_tax, "Sell tax", "Taken from the sale price")
        self._buy.editingFinished.connect(
            lambda: self._edited(self._buy, settings.set_buy_tax, settings.buy_tax)
        )
        self._sell.editingFinished.connect(
            lambda: self._edited(self._sell, settings.set_sell_tax, settings.sell_tax)
        )

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        form.addRow(_label("Buy tax (%)", self._buy), self._buy)
        form.addRow(_label("Sell tax (%)", self._sell), self._sell)

        heading = QLabel("Taxes")
        heading.setProperty("role", "title")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(heading)
        layout.addLayout(form)
        layout.addStretch(1)
        self.setMaximumWidth(480)

    def _tax_field(self, value: float, name: str, tip: str) -> QLineEdit:
        field = QLineEdit(f"{value * 100:g}")
        field.setProperty("numeric", True)
        field.setAlignment(Qt.AlignmentFlag.AlignRight)
        field.setFixedWidth(96)
        field.setToolTip(tip)
        field.setAccessibleName(f"{name} percent")
        return field

    def _edited(self, field: QLineEdit, setter: Callable[[float], None], old: float) -> None:
        try:
            value = parse_percent(field.text())
            if value is None:
                raise ValueError("empty")
            setter(value)
        except ValueError:
            _set_invalid(field, True)
            self.message.emit("Tax must be a percentage from 0 up to (not including) 100")
            return
        _set_invalid(field, False)
        field.setText(f"{value * 100:g}")
        if value != old:
            self._save(self._settings)
            self.changed.emit()


def _set_invalid(field: QLineEdit, invalid: bool) -> None:
    field.setProperty("invalid", invalid)
    field.style().unpolish(field)
    field.style().polish(field)


def _label(text: str, buddy: QWidget) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "secondary")
    label.setFixedWidth(160)
    label.setBuddy(buddy)
    return label
