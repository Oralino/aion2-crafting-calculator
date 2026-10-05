"""Header search field with a popup of matching recipes (DESIGN.md "Recipe picker")."""

from PySide6.QtCore import QStringListModel, Qt, Signal
from PySide6.QtWidgets import QCompleter, QLineEdit

from aion2calc.data.recipes import Catalog, searchable_recipes


class RecipeSearch(QLineEdit):
    chosen = Signal(int)
    not_found = Signal(str)

    def __init__(self, catalog: Catalog) -> None:
        super().__init__()
        self._entries = searchable_recipes(catalog)
        self.setPlaceholderText("Search recipes (Ctrl+K)")
        self.setAccessibleName("Search recipes")
        self.setFixedWidth(320)
        self.setClearButtonEnabled(True)
        completer = QCompleter(QStringListModel(list(self._entries)), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setMaxVisibleItems(10)
        completer.activated.connect(self.choose)
        self.setCompleter(completer)
        self.returnPressed.connect(lambda: self.choose(self.text()))

    def choose(self, text: str) -> None:
        """Open the recipe matching `text` exactly, or the only one containing it."""
        text = text.strip()
        if not text:
            return
        if text not in self._entries:
            matches = [entry for entry in self._entries if text.lower() in entry.lower()]
            if len(matches) != 1:
                if not matches:
                    self.not_found.emit(f"No recipe matches “{text}”")
                return  # several matches: the popup lists them
            text = matches[0]
        self.setText(text)
        self.chosen.emit(self._entries[text])
