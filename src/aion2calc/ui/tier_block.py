"""One tier of the chain: header with chance/combo inputs and results, and the material table."""

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import (
    QAbstractItemModel,
    QAbstractTableModel,
    QEvent,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    QPointF,
    QRect,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QBrush, QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from aion2calc.calc import TierCost
from aion2calc.session import CraftSession, MaterialRow, Source
from aion2calc.ui import theme
from aion2calc.ui.format import DASH, count, kinah, parse_kinah, parse_percent, percent

INCL, MATERIAL, QTY, COST, SOURCE, TOTAL = range(6)
HEADERS = ["Incl.", "Material", "Qty", "Cost per (Kinah)", "Source", "Total"]
WIDTHS = {INCL: 40, QTY: 56, COST: 112, SOURCE: 104, TOTAL: 120}
MATERIAL_MIN_WIDTH = 160
ROW_HEIGHT = 28

Index = QModelIndex | QPersistentModelIndex

BADGES = {
    Source.MANUAL: ("MANUAL", theme.ACCENT, theme.ACCENT),
    Source.MISSING: ("! MISSING", theme.WARNING, theme.WARNING),
    Source.CRAFTED: ("CRAFTED", theme.TEXT_SECONDARY, theme.BORDER_CONTROL),
}


class MaterialModel(QAbstractTableModel):
    edited = Signal()
    rejected = Signal(str)

    def __init__(self, session: CraftSession, tier_index: int, parent: QObject) -> None:
        super().__init__(parent)
        self._session = session
        self._tier = tier_index
        self._rows = session.rows(tier_index)
        self._mono = theme.font(13, mono=True)

    def reload(self) -> None:
        # The rows never change count, so update in place (a reset would lose the current cell).
        self._rows = self._session.rows(self._tier)
        if self._rows:
            last = self.index(len(self._rows) - 1, len(HEADERS) - 1)
            self.dataChanged.emit(self.index(0, 0), last)

    def row(self, index: Index) -> MaterialRow:
        return self._rows[index.row()]

    def rowCount(self, parent: Index | None = None) -> int:  # noqa: N802 - Qt API
        return 0 if parent is not None and parent.isValid() else len(self._rows)

    def columnCount(self, parent: Index | None = None) -> int:  # noqa: N802 - Qt API
        return 0 if parent is not None and parent.isValid() else len(HEADERS)

    def headerData(  # noqa: N802 - Qt API
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return HEADERS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return _alignment(section)
        return None

    def flags(self, index: Index) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        crafted = self.row(index).source is Source.CRAFTED
        if index.column() == INCL and not crafted:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        if index.column() == COST and not crafted:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def data(self, index: Index, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row, col = self.row(index), index.column()
        crafted = row.source is Source.CRAFTED
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.AccessibleTextRole):
            return self._display(row, col, role)
        if role == Qt.ItemDataRole.EditRole and col == COST:
            return "" if row.unit_price is None else str(row.unit_price)
        if role == Qt.ItemDataRole.CheckStateRole and col == INCL and not crafted:
            return Qt.CheckState.Unchecked if row.excluded else Qt.CheckState.Checked
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return _alignment(col)
        if role == Qt.ItemDataRole.FontRole and col in (QTY, COST, TOTAL):
            f = QFont(self._mono)
            f.setStrikeOut(col == TOTAL and row.excluded)
            return f
        if role == Qt.ItemDataRole.ForegroundRole:
            dim = row.excluded or crafted or (col in (COST, TOTAL) and row.unit_price is None)
            return QBrush(QColor(theme.TEXT_MUTED if dim else theme.TEXT_PRIMARY))
        if role == Qt.ItemDataRole.BackgroundRole and col == COST and not crafted:
            return QBrush(QColor(theme.BG_INSET))  # editable cells stay findable
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip(row, col)
        return None

    def _display(self, row: MaterialRow, col: int, role: int) -> str:
        if col == INCL and role == Qt.ItemDataRole.AccessibleTextRole:
            if row.source is Source.CRAFTED:
                return "Not bought"
            return "Excluded" if row.excluded else "Included"
        if col == MATERIAL:
            return row.name
        if col == QTY:
            return str(row.qty)
        if col == COST:
            return DASH if row.source is Source.CRAFTED else kinah(row.unit_price)
        if col == SOURCE:
            return BADGES[row.source][0]  # the delegate paints it as a badge
        if col == TOTAL:
            return DASH if row.source is Source.CRAFTED else kinah(row.total)
        return ""

    def _tooltip(self, row: MaterialRow, col: int) -> str | None:
        if row.source is Source.CRAFTED:
            return "Made by the tier below (its combo result), so it isn't bought."
        if row.excluded:
            return "Excluded from cost"
        if col == COST:
            return "Type a price and press Enter; Delete clears it."
        if col == SOURCE and row.source is Source.MISSING:
            return "No price yet: counted as 0."
        return None

    def setData(self, index: Index, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:  # noqa: N802
        if not index.isValid():
            return False
        row, col = self.row(index), index.column()
        if col == INCL and role == Qt.ItemDataRole.CheckStateRole:
            if row.source is Source.CRAFTED:
                return False
            excluded = Qt.CheckState(value) == Qt.CheckState.Unchecked
            self._session.set_excluded(self._tier, row.item_id, excluded)
        elif col == COST and role == Qt.ItemDataRole.EditRole:
            if row.source is Source.CRAFTED:
                return False
            try:
                self._session.set_price(row.item_id, parse_kinah(str(value or "")))
            except ValueError:
                self.rejected.emit(f"“{value}” isn't a Kinah amount. Use digits, e.g. 45,000.")
                return False
        else:
            return False
        self.edited.emit()
        return True

    def toggle(self, index: Index) -> None:
        incl = self.index(index.row(), INCL)
        if self.flags(incl) & Qt.ItemFlag.ItemIsUserCheckable:
            checked = self.data(incl, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
            new = Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked
            self.setData(incl, new.value, Qt.ItemDataRole.CheckStateRole)


def _alignment(col: int) -> Qt.AlignmentFlag:
    if col == INCL:
        return Qt.AlignmentFlag.AlignCenter
    horizontal = (
        Qt.AlignmentFlag.AlignRight if col in (QTY, COST, TOTAL) else Qt.AlignmentFlag.AlignLeft
    )
    return horizontal | Qt.AlignmentFlag.AlignVCenter


class CellDelegate(QStyledItemDelegate):
    """Default cells plus the focus mark: a 2px accent border on the current cell (DESIGN.md)."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        has_focus = bool(option.state & QStyle.StateFlag.State_HasFocus)
        plain = QStyleOptionViewItem(option)
        plain.state &= ~QStyle.StateFlag.State_HasFocus  # no dotted Fusion focus rect
        self.paint_cell(painter, plain, index)
        if has_focus:
            painter.save()
            painter.setPen(QPen(QColor(theme.ACCENT), 2))
            painter.drawRect(QRectF(option.rect).adjusted(1, 1, -1, -1))
            painter.restore()

    def paint_cell(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        super().paint(painter, option, index)


class BadgeDelegate(CellDelegate):
    """The Source column as an outlined badge (DESIGN.md "Badges")."""

    def paint_cell(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        model = index.model()
        if not isinstance(model, MaterialModel):
            return
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(theme.BG_SELECTED))
        text, colour, border = BADGES[model.row(index).source]
        badge_font = theme.font(11, QFont.Weight.DemiBold)
        badge_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(badge_font)
        width = painter.fontMetrics().horizontalAdvance(text) + 12
        rect = QRect(option.rect.left() + 8, option.rect.center().y() - 9, width, 18)
        painter.setPen(QColor(border))
        painter.drawRoundedRect(QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
        painter.setPen(QColor(colour))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()


class CheckDelegate(CellDelegate):
    """The Incl. checkbox drawn to DESIGN.md: 16px, `border.control` outline (3:1 on every
    surface), gold fill with a dark tick when checked. Fusion's own box is too faint here."""

    def paint_cell(self, painter: QPainter, option: QStyleOptionViewItem, index: Index) -> None:
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(theme.BG_SELECTED))
        state = index.data(Qt.ItemDataRole.CheckStateRole)
        if state is None:
            return  # crafted rows have no checkbox
        box = QRectF(0, 0, 16, 16)
        box.moveCenter(QRectF(option.rect).center())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        checked = state == Qt.CheckState.Checked
        painter.setPen(QPen(QColor(theme.ACCENT if checked else theme.BORDER_CONTROL), 1))
        painter.setBrush(QColor(theme.ACCENT if checked else theme.BG_INSET))
        painter.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 3, 3)
        if checked:
            painter.setPen(QPen(QColor(theme.ON_ACCENT), 2))
            left, top = box.left(), box.top()
            painter.drawPolyline(
                [
                    QPointF(left + 4, top + 8.5),
                    QPointF(left + 7, top + 11.5),
                    QPointF(left + 12, top + 5),
                ]
            )
        painter.restore()

    def editorEvent(  # noqa: N802 - Qt API
        self,
        event: QEvent,
        model: QAbstractItemModel,
        option: QStyleOptionViewItem,
        index: Index,
    ) -> bool:
        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and isinstance(event, QMouseEvent)
            and event.button() == Qt.MouseButton.LeftButton
            and isinstance(model, MaterialModel)
        ):
            model.toggle(index)
            return True
        return event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick)


class _TableKeys(QObject):
    """Enter edits, Delete clears a manual price, Space toggles Incl. (DESIGN.md keyboard)."""

    def __init__(self, table: QTableView, model: MaterialModel) -> None:
        super().__init__(table)
        self._table, self._model = table, model

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 - Qt API
        if event.type() != QEvent.Type.KeyPress or not isinstance(event, QKeyEvent):
            return False
        index = self._table.currentIndex()
        if not index.isValid() or self._table.state() == QTableView.State.EditingState:
            return False
        cost = index.siblingAtColumn(COST)
        editable = bool(self._model.flags(cost) & Qt.ItemFlag.ItemIsEditable)
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F2):
            if editable:
                self._table.setCurrentIndex(cost)
                self._table.edit(cost)
            return True
        if key == Qt.Key.Key_Delete:
            if editable:
                self._model.setData(cost, "")
            return True
        if key == Qt.Key.Key_Space:
            self._model.toggle(index)
            return True
        return False


def _label(text: str, role: str, buddy: QWidget | None = None) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    if buddy is not None:
        label.setBuddy(buddy)
    return label


class _RateField(QLineEdit):
    def __init__(self, accessible_name: str) -> None:
        super().__init__()
        self.setProperty("numeric", True)
        self.setFixedWidth(72)
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setAccessibleName(accessible_name)

    def set_invalid(self, invalid: bool) -> None:
        self.setProperty("invalid", invalid)
        self.style().unpolish(self)
        self.style().polish(self)


class TierBlock(QFrame):
    changed = Signal()
    message = Signal(str)

    def __init__(self, session: CraftSession, tier_index: int) -> None:
        super().__init__()
        self._session = session
        self._index = tier_index
        settings = session.tiers[tier_index]
        item_id = settings.recipe.item_id
        recipe_name = session.name(item_id)
        grade = session.grade(item_id)
        colour = theme.grade_colour(grade)
        self.setObjectName("tier")
        self.setStyleSheet(f"QFrame#tier {{ border-left: 4px solid {colour}; }}")

        name = _label(recipe_name, "title")
        name.setStyleSheet(f"color: {colour};")
        where = f"Tier {tier_index + 1} of {len(session.tiers)}"
        caption = _label(f"{where} · {grade}" if grade else where, "caption")

        self.chance = _RateField(f"Craft chance percent, {recipe_name}")
        self.chance.setPlaceholderText("100%")
        self.chance.setText(percent(settings.chance).removesuffix("%"))
        self.chance.setToolTip("Your in-game craft success rate for this recipe, e.g. 93.1")
        self.combo = _RateField(f"Combo chance percent, {recipe_name}")
        self.combo.setText(percent(settings.combo_rate).removesuffix("%"))
        top_tier = tier_index == len(session.tiers) - 1
        self.combo.setToolTip(
            "Chance a successful craft gives the Splendent version (counts in the expected sale)"
            if top_tier
            else "Chance a successful craft gives the Splendent (combo) item the next tier needs"
        )
        # Every lower tier feeds the next one; the top tier's combo only matters if it has one.
        self.has_combo = not top_tier or session.final_combo_item is not None
        self.chance.editingFinished.connect(self._chance_edited)
        self.combo.editingFinished.connect(self._combo_edited)

        self._successes = _label("", "num")
        self._crafts = _label("", "num")
        self._cost = _label("", "num-strong")
        self._lost = _label("", "num-secondary")
        self._lost.setToolTip(
            "Spent on crafts that failed; part of the tier cost."
            if top_tier
            else "Spent on crafts that failed or didn't combo; part of the tier cost."
        )

        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(name)
        top.addWidget(caption)
        top.addStretch(1)
        top.addWidget(_label("Tier cost", "secondary"))
        top.addWidget(self._cost)
        top.addSpacing(16)
        top.addWidget(_label("Lost", "secondary"))
        top.addWidget(self._lost)

        inputs = QHBoxLayout()
        inputs.setSpacing(8)
        inputs.addWidget(_label("Chance", "label", self.chance))
        inputs.addWidget(self.chance)
        if self.has_combo:
            inputs.addSpacing(8)
            inputs.addWidget(_label("Combo", "label", self.combo))
            inputs.addWidget(self.combo)
        else:
            self.combo.hide()
        inputs.addSpacing(16)
        inputs.addWidget(_label("Successes", "secondary"))
        inputs.addWidget(self._successes)
        inputs.addSpacing(8)
        inputs.addWidget(_label("Crafts", "secondary"))
        inputs.addWidget(self._crafts)
        inputs.addStretch(1)

        self.table = QTableView()
        self.model = MaterialModel(session, tier_index, parent=self.table)
        self.model.edited.connect(self.changed)
        self.model.rejected.connect(self.message)
        self.table.setModel(self.model)
        self.table.setAccessibleName(f"Materials, {recipe_name}")
        self.table.setItemDelegate(CellDelegate(self.table))
        self.table.setItemDelegateForColumn(INCL, CheckDelegate(self.table))
        self.table.setItemDelegateForColumn(SOURCE, BadgeDelegate(self.table))
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(
            QTableView.EditTrigger.DoubleClicked | QTableView.EditTrigger.AnyKeyPressed
        )
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        header = self.table.horizontalHeader()
        header.setFixedHeight(ROW_HEIGHT)
        header.setHighlightSections(False)
        header.setSectionResizeMode(MATERIAL, QHeaderView.ResizeMode.Stretch)
        for column, width in WIDTHS.items():
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        self.table.setMinimumWidth(MATERIAL_MIN_WIDTH + sum(WIDTHS.values()))
        self.table.installEventFilter(_TableKeys(self.table, self.model))
        self.table.setFixedHeight(ROW_HEIGHT * (self.model.rowCount() + 1) + 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        layout.addLayout(top)
        layout.addLayout(inputs)
        layout.addWidget(self.table)

    def focus_chain(self) -> list[QWidget]:
        """This block's inputs in tab order."""
        return [self.chance, *([self.combo] if self.has_combo else []), self.table]

    def _chance_edited(self) -> None:
        self._rate_edited(self.chance, lambda v: self._session.set_chance(self._index, v))

    def _combo_edited(self) -> None:
        def set_combo(value: float | None) -> None:
            if value is None:
                raise ValueError("combo rate is required")
            self._session.set_combo_rate(self._index, value)

        self._rate_edited(self.combo, set_combo)

    def _rate_edited(self, field: _RateField, setter: Callable[[float | None], None]) -> None:
        settings = self._session.tiers[self._index]
        before = (settings.chance, settings.combo_rate)
        try:
            setter(parse_percent(field.text()))
        except ValueError:
            field.set_invalid(True)
            self.message.emit("Enter a percentage above 0 and up to 100, e.g. 93.1")
            return
        field.set_invalid(False)
        if (settings.chance, settings.combo_rate) != before:
            self.changed.emit()

    def refresh(self, cost: TierCost) -> None:
        self.model.reload()
        self._successes.setText(count(cost.successes))
        self._crafts.setText(count(cost.attempts))
        self._cost.setText(kinah(cost.cost))
        self._lost.setText(kinah(cost.lost))
