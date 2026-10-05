"""Remembered settings (Windows registry via QSettings). Bad stored values fall back to defaults."""

from PySide6.QtCore import QSettings

from aion2calc.session import Settings, check_tax

ORGANISATION = APP = "Aion2CraftingCalculator"


def _store() -> QSettings:
    return QSettings(ORGANISATION, APP)


def _tax(stored: QSettings, key: str, default: float) -> float:
    try:
        return check_tax(float(stored.value(key, default)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def load_settings(stored: QSettings | None = None) -> Settings:
    stored = stored or _store()
    defaults = Settings()
    return Settings(
        buy_tax=_tax(stored, "tax/buy", defaults.buy_tax),
        sell_tax=_tax(stored, "tax/sell", defaults.sell_tax),
    )


def save_settings(settings: Settings, stored: QSettings | None = None) -> None:
    stored = stored or _store()
    stored.setValue("tax/buy", settings.buy_tax)
    stored.setValue("tax/sell", settings.sell_tax)
