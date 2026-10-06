"""SQLite price store: every market reading (history) plus the user's manual prices.

Lives in the user's app-data folder, not next to the .exe. Prices are per item id; faction copies
of an item share a name and a market, so a reading is stored for each of its ids.
"""

import os
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

SCHEMA_VERSION = 1


class PriceSource(Enum):
    OCR = "ocr"
    MANUAL = "manual"


@dataclass(frozen=True)
class Observation:
    item_id: int
    unit_price: int
    listings: int | None
    observed_at: datetime
    source: PriceSource


def default_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "Aion2CraftingCalculator" / "prices.sqlite3"


def _now() -> datetime:
    return datetime.now(UTC)


class PriceStore:
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path))
        self._db.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    def close(self) -> None:
        self._db.close()

    def _migrate(self) -> None:
        version = self._db.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(f"price database is from a newer app (schema {version})")
        if version < 1:
            with self._db:
                self._db.executescript(
                    """
                    CREATE TABLE observation (
                        id INTEGER PRIMARY KEY,
                        item_id INTEGER NOT NULL,
                        unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                        listings INTEGER,
                        observed_at TEXT NOT NULL,
                        source TEXT NOT NULL CHECK (source IN ('ocr', 'manual'))
                    );
                    CREATE INDEX observation_item_time ON observation (item_id, observed_at);
                    CREATE TABLE manual_price (
                        item_id INTEGER PRIMARY KEY,
                        unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
                        updated_at TEXT NOT NULL
                    );
                    PRAGMA user_version = 1;
                    """
                )

    def record_ocr(
        self,
        readings: Iterable[tuple[Iterable[int], int, int | None]],
        at: datetime | None = None,
    ) -> int:
        """Store (item ids, lowest price, listings) from one capture; returns rows added.

        A capture is newer than any typed price, so it clears the manual price of each item read
        (the typed price stays in the history). An item listed more than once in one capture
        (e.g. equipment with different stats) keeps its lowest price."""
        when = (at or _now()).isoformat()
        lowest: dict[int, tuple[int, int | None]] = {}
        for item_ids, price, listings in readings:
            for item_id in item_ids:
                if item_id not in lowest or price < lowest[item_id][0]:
                    lowest[item_id] = (price, listings)
        rows = [
            (item_id, price, listings, when, PriceSource.OCR.value)
            for item_id, (price, listings) in lowest.items()
        ]
        with self._db:
            self._db.executemany(
                "INSERT INTO observation (item_id, unit_price, listings, observed_at, source) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
            self._db.executemany(
                "DELETE FROM manual_price WHERE item_id = ?", [(row[0],) for row in rows]
            )
        return len(rows)

    def set_manual(self, item_id: int, price: int | None, at: datetime | None = None) -> None:
        """Set (and log) a manual price, or clear it with None."""
        when = (at or _now()).isoformat()
        with self._db:
            if price is None:
                self._db.execute("DELETE FROM manual_price WHERE item_id = ?", (item_id,))
                return
            self._db.execute(
                "INSERT INTO manual_price (item_id, unit_price, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT (item_id) DO UPDATE SET unit_price = excluded.unit_price, "
                "updated_at = excluded.updated_at",
                (item_id, price, when),
            )
            self._db.execute(
                "INSERT INTO observation (item_id, unit_price, listings, observed_at, source) "
                "VALUES (?, ?, NULL, ?, ?)",
                (item_id, price, when, PriceSource.MANUAL.value),
            )

    def manual_prices(self) -> dict[int, int]:
        return dict(self._db.execute("SELECT item_id, unit_price FROM manual_price").fetchall())

    def latest_ocr(self) -> dict[int, Observation]:
        """The newest OCR reading per item."""
        rows = self._db.execute(
            "SELECT item_id, unit_price, listings, observed_at FROM observation o "
            "WHERE source = 'ocr' AND observed_at = ("
            "  SELECT MAX(observed_at) FROM observation "
            "  WHERE item_id = o.item_id AND source = 'ocr')"
        ).fetchall()
        return {
            item_id: Observation(
                item_id, price, listings, datetime.fromisoformat(at), PriceSource.OCR
            )
            for item_id, price, listings, at in rows
        }

    def history(self, item_id: int) -> list[Observation]:
        rows = self._db.execute(
            "SELECT unit_price, listings, observed_at, source FROM observation "
            "WHERE item_id = ? ORDER BY observed_at",
            (item_id,),
        ).fetchall()
        return [
            Observation(item_id, price, listings, datetime.fromisoformat(at), PriceSource(src))
            for price, listings, at, src in rows
        ]
