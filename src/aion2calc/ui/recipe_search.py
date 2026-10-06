"""Header search field with a dropdown of matching recipes (DESIGN.md "Recipe picker").

The dropdown lists every recipe whose name contains all the typed words, in any order ("neck
ruby" finds Ruby Necklace), names starting with the text first.
"""

from PySide6.QtCore import QStringListModel, Signal
from PySide6.QtWidgets import QCompleter, QLineEdit

from aion2calc.data.recipes import Catalog, searchable_recipes

MAX_SHOWN = 50


def matching(entries: list[str], text: str) -> list[str]:
    """Entries containing every word of `text`; those starting with it first, then by name."""
    query = text.strip().lower()
    words = query.split()
    if not words:
        return []
    found = [e for e in entries if all(w in e.lower() for w in words)]
    return sorted(found, key=lambda e: (not e.lower().startswith(query), e.lower()))


class RecipeSearch(QLineEdit):
    chosen = Signal(int)
    not_found = Signal(str)

    def __init__(self, catalog: Catalog) -> None:
        super().__init__()
        self._entries = searchable_recipes(catalog)
        self._names = list(self._entries)
        self.setPlaceholderText("Search recipes (Ctrl+K)")
        self.setAccessibleName("Search recipes")
        self.setFixedWidth(320)
        self.setClearButtonEnabled(True)
        self._model = QStringListModel(self)
        self.completer_ = QCompleter(self._model, self)
        # We filter ourselves (any word order), so the completer just shows the list.
        self.completer_.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        self.completer_.setMaxVisibleItems(10)
        self.completer_.setWidget(self)
        self.completer_.activated.connect(self.choose)
        self.textEdited.connect(self._update_dropdown)
        self.returnPressed.connect(lambda: self.choose(self.text()))

    def _update_dropdown(self, text: str) -> None:
        found = matching(self._names, text)[:MAX_SHOWN]
        self._model.setStringList(found)
        if found:
            self.completer_.complete()
        else:
            self._hide_dropdown()

    def _hide_dropdown(self) -> None:
        if (popup := self.completer_.popup()) is not None:
            popup.hide()

    def choose(self, text: str) -> None:
        """Open the recipe matching `text` exactly, or the only one containing its words."""
        text = text.strip()
        if not text:
            return
        if text not in self._entries:
            found = matching(self._names, text)
            if len(found) != 1:
                if not found:
                    self.not_found.emit(f"No recipe matches “{text}”")
                else:
                    self._update_dropdown(text)  # several: show them to pick from
                return
            text = found[0]
        self._hide_dropdown()
        self.setText(text)
        self.chosen.emit(self._entries[text])
