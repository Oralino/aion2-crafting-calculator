import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from aion2calc.data.recipes import Catalog
from aion2calc.ui import theme
from aion2calc.ui.main_window import MainWindow
from aion2calc.ui.settings_store import load_settings

# Dev layout: <repo>/src/aion2calc/app.py → <repo>/data/recipes.json. Packaging will bundle it.
RECIPES = Path(__file__).resolve().parents[2] / "data" / "recipes.json"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Aion2 Crafting Calculator")
    theme.apply(app)
    window = MainWindow(Catalog.load(RECIPES), load_settings())
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
