"""Number formatting and parsing for display (DESIGN.md "Number formatting"). Pure; no Qt."""

import math
import re

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
