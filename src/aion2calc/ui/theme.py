"""Design tokens from brain/design/DESIGN.md: the one place colours, fonts and sizes are defined.

The QSS sheet and QPalette are generated from these; widgets never hard-code hex values.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

FONTS_DIR = Path(__file__).parent / "fonts"
"""Inter and JetBrains Mono static TTFs, SIL Open Font License 1.1 (licence files alongside)."""

# Surfaces and borders
BG_APP = "#000000"
BG_SURFACE = "#1A1A1A"
BG_RAISED = "#242424"
BG_INSET = "#0D0D0D"
BG_SELECTED = "#2B2616"
BORDER_SUBTLE = "#333333"
BORDER_CONTROL = "#707070"
SCROLL_HANDLE = "#4D4D4D"

# Text
TEXT_PRIMARY = "#E8E6E1"
TEXT_SECONDARY = "#B3B3B3"
TEXT_MUTED = "#8F8F8F"
TEXT_DISABLED = "#666666"

# Accent
ACCENT = "#C9A84C"
ACCENT_HOVER = "#D4B65E"
ACCENT_PRESSED = "#A88A3A"
ON_ACCENT = "#0D0D0D"

# Item grades (Global)
GRADE_COLOURS = {
    "Common": "#9E9E9E",
    "Rare": "#5DBB63",
    "Epic": "#5B9BE6",
    "Unique": "#F2D43D",
}

# Status
POSITIVE = "#4FC3A1"
WARNING = "#F0D875"
DANGER = "#EF6B6B"

# Bundled fonts first, Windows fallbacks if they fail to load.
UI_FONTS = ["Inter", "Segoe UI"]
MONO_FONTS = ["JetBrains Mono", "Consolas"]


def grade_colour(grade: str | None) -> str:
    return GRADE_COLOURS.get(grade or "", TEXT_PRIMARY)


def font(size_px: int, weight: QFont.Weight = QFont.Weight.Normal, mono: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(MONO_FONTS if mono else UI_FONTS)
    f.setPixelSize(size_px)
    f.setWeight(weight)
    return f


def _css_fonts(families: list[str]) -> str:
    return ", ".join(f'"{name}"' for name in families)


def palette() -> QPalette:
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: BG_SURFACE,
        QPalette.ColorRole.WindowText: TEXT_PRIMARY,
        QPalette.ColorRole.Text: TEXT_PRIMARY,
        QPalette.ColorRole.ButtonText: TEXT_PRIMARY,
        QPalette.ColorRole.Base: BG_INSET,
        QPalette.ColorRole.AlternateBase: BG_SURFACE,
        QPalette.ColorRole.Button: BG_RAISED,
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: ON_ACCENT,
        QPalette.ColorRole.PlaceholderText: TEXT_MUTED,
        QPalette.ColorRole.ToolTipBase: BG_RAISED,
        QPalette.ColorRole.ToolTipText: TEXT_PRIMARY,
        QPalette.ColorRole.Link: ACCENT,
        QPalette.ColorRole.Mid: BORDER_SUBTLE,
        QPalette.ColorRole.Dark: BORDER_SUBTLE,
    }
    for role, colour in roles.items():
        p.setColor(role, QColor(colour))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_DISABLED))
    return p


def stylesheet() -> str:
    ui, mono = _css_fonts(UI_FONTS), _css_fonts(MONO_FONTS)
    return f"""
* {{ font-family: {ui}; font-size: 13px; color: {TEXT_PRIMARY}; }}
QMainWindow, QWidget#app {{ background: {BG_APP}; }}
QToolTip {{ background: {BG_RAISED}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_SUBTLE};
    padding: 4px 8px; font-size: 12px; }}

QWidget#header, QWidget#summary, QStatusBar, QFrame#tier {{ background: {BG_SURFACE}; }}
QWidget#header {{ border-bottom: 1px solid {BORDER_SUBTLE}; }}
QWidget#summary {{ border-left: 1px solid {BORDER_SUBTLE}; }}
QStatusBar {{ border-top: 1px solid {BORDER_SUBTLE}; min-height: 28px; font-size: 12px;
    color: {TEXT_SECONDARY}; padding-left: 16px; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ font-size: 12px; color: {TEXT_SECONDARY}; padding-right: 16px; }}
QFrame#tier {{ border: 1px solid {BORDER_SUBTLE}; border-radius: 6px; }}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: {BG_APP}; border: none; }}

QLabel[role="heading"] {{ font-size: 18px; font-weight: 600; }}
QLabel[role="title"] {{ font-size: 14px; font-weight: 600; }}
QLabel[role="label"] {{ font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY}; }}
QLabel[role="caption"] {{ font-size: 12px; color: {TEXT_SECONDARY}; }}
QLabel[role="muted"] {{ color: {TEXT_MUTED}; }}
QLabel[role="secondary"] {{ color: {TEXT_SECONDARY}; }}
QLabel[role="num"] {{ font-family: {mono}; }}
QLabel[role="num-strong"] {{ font-family: {mono}; font-weight: 600; }}
QLabel[role="num-secondary"] {{ font-family: {mono}; color: {TEXT_SECONDARY}; }}
QLabel[role="display"] {{ font-family: {mono}; font-size: 20px; font-weight: 600; }}
QLabel[role="warning"] {{ font-size: 12px; color: {WARNING}; }}
QLabel[tone="positive"] {{ color: {POSITIVE}; }}
QLabel[tone="danger"] {{ color: {DANGER}; }}
QLabel[tone="muted"] {{ color: {TEXT_MUTED}; }}

QLineEdit {{ background: {BG_INSET}; border: 1px solid {BORDER_CONTROL}; border-radius: 4px;
    padding: 0 8px; min-height: 30px; selection-background-color: {BG_SELECTED};
    selection-color: {TEXT_PRIMARY}; }}
QLineEdit:focus {{ border: 2px solid {ACCENT}; padding: 0 7px; }}
QLineEdit[invalid="true"] {{ border: 2px solid {DANGER}; padding: 0 7px; }}
QLineEdit[numeric="true"] {{ font-family: {mono}; }}

QTabBar {{ background: transparent; }}
QTabBar::tab {{ background: transparent; color: {TEXT_SECONDARY}; font-size: 12px;
    font-weight: 600; padding: 0 16px; min-height: 38px; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ color: {TEXT_PRIMARY}; }}
QTabBar::tab:selected {{ color: {TEXT_PRIMARY}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:focus {{ border: 2px solid {ACCENT}; }}

QTableView {{ background: {BG_SURFACE}; border: none; gridline-color: {BORDER_SUBTLE};
    selection-background-color: {BG_SELECTED}; selection-color: {TEXT_PRIMARY}; }}
QTableView:focus {{ outline: none; }}
QHeaderView::section {{ background: {BG_RAISED}; color: {TEXT_SECONDARY}; font-size: 12px;
    font-weight: 600; border: none; border-bottom: 1px solid {BORDER_SUBTLE}; padding: 0 8px;
    min-height: 28px; }}

QListView {{ background: {BG_RAISED}; border: 1px solid {BORDER_SUBTLE}; }}
QListView::item {{ min-height: 32px; padding: 0 8px; }}
QListView::item:selected {{ background: {BG_SELECTED}; color: {TEXT_PRIMARY}; }}

QScrollBar:vertical {{ width: 10px; background: transparent; }}
QScrollBar:horizontal {{ height: 10px; background: transparent; }}
QScrollBar::handle {{ background: {SCROLL_HANDLE}; border-radius: 5px; min-height: 24px;
    min-width: 24px; }}
QScrollBar::handle:hover {{ background: {BORDER_CONTROL}; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    background: none; border: none; width: 0; height: 0; }}

QFrame[role="divider"] {{ background: {BORDER_SUBTLE}; max-height: 1px; min-height: 1px; }}
"""


def load_fonts() -> list[str]:
    """Register the bundled fonts; returns the families Qt loaded."""
    families: set[str] = set()
    for path in sorted(FONTS_DIR.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.update(QFontDatabase.applicationFontFamilies(font_id))
    return sorted(families)


def apply(app: QApplication) -> None:
    load_fonts()
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)  # dark title bar on light-mode Windows
    app.setPalette(palette())
    app.setStyleSheet(stylesheet())
