"""Number formatting and parsing for display (DESIGN.md "Number formatting"). Pure; no Qt."""

import math
import re
from datetime import datetime, timedelta

MINUS = "−"
DASH = "—"


def kinah(value: float | None) -> str:
    """`1,234,567`; rounded for display only; U+2212 for negatives; `—` when missing."""
    if value is None or not math.isfinite(value):
        return DASH
    rounded = round(value)
    text = f"{abs(rounded):,}"
    return f"{MINUS}{text}" if rounded < 0 else text


def signed_kinah(value: float) -> str:
    """`+1,234` / `−1,234` for tax lines and profit."""
    return f"+{kinah(value)}" if round(value) > 0 else kinah(value)


def count(value: float) -> str:
    """Successes and crafts: one decimal."""
    return f"{value:.1f}"


def percent(fraction: float | None) -> str:
    """A fraction as `93.1%`; empty when not set."""
    return "" if fraction is None else f"{fraction * 100:.1f}%"


STALE_AFTER = timedelta(hours=24)
"""Prices older than this are flagged (DESIGN.md suggests 24h; owner may change it later)."""


def age(then: datetime, now: datetime) -> str:
    """Compact age of a reading: `now`, `12m`, `5h`, `3d`."""
    seconds = max(0, int((now - then).total_seconds()))
    if seconds < 60:
        return "now"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def is_stale(then: datetime, now: datetime) -> bool:
    return now - then > STALE_AFTER


def parse_kinah(text: str) -> int | None:
    """User-typed Kinah (`1,234`, `1234`, ` 1 234 `). Empty means no value; else invalid."""
    cleaned = re.sub(r"[\s,]", "", text)
    if not cleaned:
        return None
    if not cleaned.isdigit() or len(cleaned) > 13:  # 13 digits: up to MAX_KINAH
        raise ValueError(f"not a Kinah amount: {text!r}")
    return int(cleaned)


def parse_percent(text: str) -> float | None:
    """User-typed percentage (`93.1`, `93.12%`, `0`) as a fraction. Empty means not set; range
    checks belong to whoever uses the value (rates and taxes have different ranges)."""
    cleaned = text.strip().removesuffix("%").strip()
    if not cleaned:
        return None
    value = float(cleaned)
    if not math.isfinite(value):
        raise ValueError(f"not a percentage: {text!r}")
    return value / 100
