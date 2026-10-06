import sqlite3
import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType

from PySide6.QtWidgets import QApplication, QMessageBox

from aion2calc.capture.hotkey import GlobalHotkey
from aion2calc.capture.window import CaptureError, active_game_window, grab
from aion2calc.capture.worker import CaptureReader
from aion2calc.data.prices import PriceStore, default_path
from aion2calc.data.recipes import Catalog
from aion2calc.ui import theme
from aion2calc.ui.main_window import MainWindow
from aion2calc.ui.settings_store import load_settings

# Dev layout: <repo>/src/aion2calc/app.py → <repo>/data/recipes.json. The .exe bundles it as
# data/recipes.json next to its own files (PyInstaller's sys._MEIPASS, see aion2calc.spec).
_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
RECIPES = _ROOT / "data" / "recipes.json"
TITLE = "Aion2 Crafting Calculator"


def _report_error(
    kind: type[BaseException], error: BaseException, trace: TracebackType | None
) -> None:
    """Unexpected errors: the .exe has no console, so log them next to the price database and
    say so, instead of failing silently."""
    log = default_path().parent / "error.log"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as file:
            file.write(f"{datetime.now().isoformat()}\n")
            file.write("".join(traceback.format_exception(kind, error, trace)) + "\n")
        where = f"Details were saved to {log}"
    except OSError:
        where = "The details couldn't be saved."
    QMessageBox.critical(None, TITLE, f"Something went wrong: {error}\n\n{where}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(TITLE)
    sys.excepthook = _report_error
    theme.apply(app)
    try:
        catalog = Catalog.load(RECIPES)
        store = PriceStore(default_path())
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
        # A packaged .exe has no console, so say what went wrong instead of closing silently.
        QMessageBox.critical(None, TITLE, f"Couldn't start: {error}")
        return 1
    window = MainWindow(catalog, load_settings(), store)

    reader = CaptureReader(catalog, app)
    reader.done.connect(window.apply_reading)
    reader.failed.connect(lambda message: window.show_message(f"Capture failed: {message}"))

    hotkey = GlobalHotkey(app)

    def capture() -> None:
        try:
            image = grab(active_game_window())
        except CaptureError as error:
            window.show_message(f"Capture failed: {error}")
            return
        except OSError as error:
            window.show_message(f"Capture failed: couldn't read the screen ({error})")
            return
        if reader.read(image):
            window.capture_started()
        else:
            window.show_message("Still reading the last capture; try again in a moment")

    if hotkey.registered:
        hotkey.pressed.connect(capture)
        window.set_capture_label(f"Capture: {hotkey.label}")
    else:
        window.set_capture_label(f"Capture: {hotkey.label} unavailable (another app uses it)")

    window.show()
    code = app.exec()
    reader.stop()
    store.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
