import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aion2calc.data.prices import PriceSource, PriceStore

T0 = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


@pytest.fixture
def store() -> PriceStore:
    return PriceStore(":memory:")


def test_latest_ocr_per_item(store: PriceStore) -> None:
    store.record_ocr([((1, 2), 4_000, 55)], at=T0)
    store.record_ocr([((1, 2), 3_999, 50), ((3,), 95_000, 130)], at=T0 + timedelta(hours=1))
    latest = store.latest_ocr()
    assert {i: o.unit_price for i, o in latest.items()} == {1: 3_999, 2: 3_999, 3: 95_000}
    assert latest[1].listings == 50
    assert latest[1].observed_at == T0 + timedelta(hours=1)


def test_manual_price_set_clear_and_history(store: PriceStore) -> None:
    store.set_manual(5, 1_000, at=T0)
    store.set_manual(5, 1_200, at=T0 + timedelta(minutes=5))
    assert store.manual_prices() == {5: 1_200}
    store.set_manual(5, None)
    assert store.manual_prices() == {}
    history = store.history(5)
    assert [o.unit_price for o in history] == [1_000, 1_200]  # clearing isn't a price
    assert all(o.source is PriceSource.MANUAL for o in history)
    assert store.latest_ocr() == {}  # manual prices aren't OCR readings


def test_a_capture_replaces_typed_prices_of_the_items_it_read(store: PriceStore) -> None:
    store.set_manual(1, 5_000, at=T0)
    store.set_manual(7, 800, at=T0)
    store.record_ocr([((1, 2), 4_000, 55)], at=T0 + timedelta(minutes=1))
    assert store.manual_prices() == {7: 800}  # item 7 wasn't in the capture
    assert [o.unit_price for o in store.history(1)] == [5_000, 4_000]


def test_an_item_listed_twice_in_one_capture_keeps_its_lowest_price(store: PriceStore) -> None:
    store.record_ocr([((1,), 5_000, 3), ((1,), 4_200, 1)], at=T0)
    assert store.latest_ocr()[1].unit_price == 4_200
    assert len(store.history(1)) == 1


def test_persists_on_disk(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "prices.sqlite3"
    first = PriceStore(path)
    first.set_manual(1, 10)
    first.close()
    second = PriceStore(path)
    assert second.manual_prices() == {1: 10}
    second.close()


def test_refuses_a_newer_schema(tmp_path: Path) -> None:
    path = tmp_path / "prices.sqlite3"
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version = 99")
    db.close()
    with pytest.raises(RuntimeError):
        PriceStore(path)


def test_negative_prices_are_rejected_by_the_database(store: PriceStore) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.set_manual(1, -5)
