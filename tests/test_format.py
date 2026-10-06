import math
from datetime import UTC, datetime, timedelta

import pytest

from aion2calc.ui.format import (
    age,
    count,
    is_stale,
    kinah,
    parse_kinah,
    parse_percent,
    percent,
    signed_kinah,
)


def test_kinah() -> None:
    assert kinah(1_234_567.4) == "1,234,567"
    assert kinah(-1_500) == "−1,500"
    assert kinah(None) == "—"
    assert kinah(math.nan) == "—"
    assert signed_kinah(250) == "+250"
    assert signed_kinah(-250) == "−250"


def test_counts_and_percent() -> None:
    assert count(68.7275) == "68.7"
    assert percent(0.93121) == "93.1%"
    assert percent(None) == ""


@pytest.mark.parametrize(("text", "value"), [("1,234", 1234), (" 1 234 ", 1234), ("", None)])
def test_parse_kinah(text: str, value: int | None) -> None:
    assert parse_kinah(text) == value


@pytest.mark.parametrize("text", ["12k", "-5", "1.5"])
def test_parse_kinah_rejects(text: str) -> None:
    with pytest.raises(ValueError):
        parse_kinah(text)


def test_parse_percent() -> None:
    assert parse_percent("93.12%") == pytest.approx(0.9312)
    assert parse_percent("0") == 0
    assert parse_percent(" ") is None
    for bad in ["x", "nan", "inf"]:
        with pytest.raises(ValueError):
            parse_percent(bad)


def test_parse_kinah_caps_length() -> None:
    assert parse_kinah("9" * 13) == 10**13 - 1
    with pytest.raises(ValueError):
        parse_kinah("9" * 14)


def test_age_and_staleness() -> None:
    now = datetime(2026, 10, 5, 12, tzinfo=UTC)
    assert age(now - timedelta(seconds=30), now) == "now"
    assert age(now - timedelta(minutes=12), now) == "12m"
    assert age(now - timedelta(hours=5), now) == "5h"
    assert age(now - timedelta(days=3), now) == "3d"
    assert age(now + timedelta(minutes=1), now) == "now"  # clock skew
    assert not is_stale(now - timedelta(hours=23), now)
    assert is_stale(now - timedelta(hours=25), now)
