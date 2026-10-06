"""Read the Market → Exchange search list: item name, listing count and lowest price per row.

Layout is found, not hard-coded (it moves with resolution and aspect ratio): RapidOCR finds the
"Sales List" and "Lowest Sale Price" header labels (columns) and the item names (rows); numbers in
each row are read with digit templates (see `digits.py`). Rows whose numbers can't be read
cleanly — 0 listings (dimmed), cut off by scrolling, unknown names — yield no price, never a guess.
"""

import difflib
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from statistics import median
from typing import Any

from PIL import Image

from aion2calc.ocr.digits import DigitTemplates, digit_height, parse_number


@dataclass(frozen=True)
class TextBox:
    text: str
    left: float
    top: float
    right: float
    bottom: float

    @property
    def x(self) -> float:
        return (self.left + self.right) / 2

    @property
    def y(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        return self.bottom - self.top


OcrEngine = Callable[[Image.Image], list[TextBox]]


@dataclass(frozen=True)
class RowCells:
    """One list row before its numbers are read."""

    text: str
    listings: Image.Image
    price: Image.Image


@dataclass(frozen=True)
class MarketRow:
    text: str
    """The name as OCR read it."""
    name: str | None
    """The catalog name it matched, or None."""
    item_ids: tuple[int, ...]
    exact: bool
    """False when the name only matched approximately (show it for review)."""
    listings: int | None
    price: int | None
    """Lowest sale price; None when there are no listings or it couldn't be read cleanly."""


@dataclass(frozen=True)
class MarketReading:
    rows: tuple[MarketRow, ...]
    problem: str | None = None
    """Why nothing could be read (e.g. the market list isn't on screen)."""

    @property
    def priced(self) -> tuple[MarketRow, ...]:
        """Rows safe to store: an exact name match with a read price."""
        return tuple(r for r in self.rows if r.exact and r.price is not None and r.listings)

    @property
    def approximate(self) -> tuple[MarketRow, ...]:
        """Priced rows whose name only matched approximately: shown for checking, never stored
        (an uncatalogued item with a similar name would otherwise overwrite a real price)."""
        return tuple(r for r in self.rows if not r.exact and r.price is not None and r.listings)


def rapidocr_engine() -> OcrEngine:
    """RapidOCR with its English recognition model (slow to create; reuse it)."""
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

    engine = RapidOCR(
        params={
            "Rec.lang_type": LangRec.EN,
            "Rec.ocr_version": OCRVersion.PPOCRV5,
            "Rec.model_type": ModelType.MOBILE,
        }
    )

    def run(image: Image.Image) -> list[TextBox]:
        import numpy as np

        result: Any = engine(np.asarray(image.convert("RGB")))
        if not result.txts:
            return []
        return [
            TextBox(
                str(text),
                float(min(p[0] for p in box)),
                float(min(p[1] for p in box)),
                float(max(p[0] for p in box)),
                float(max(p[1] for p in box)),
            )
            for box, text in zip(result.boxes, result.txts, strict=True)
        ]

    return run


def normalise_name(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


class NameMatcher:
    """Matches OCR'd names to catalog item names (faction copies share a name, so one name can
    mean several item ids)."""

    def __init__(self, names: Mapping[int, str], cutoff: float = 0.9) -> None:
        self._ids: dict[str, list[int]] = {}
        self._display: dict[str, str] = {}
        for item_id, name in names.items():
            key = normalise_name(name)
            self._ids.setdefault(key, []).append(item_id)
            self._display.setdefault(key, name)
        self._keys = list(self._ids)
        self._cutoff = cutoff

    def match(self, text: str) -> tuple[str, tuple[int, ...], bool] | None:
        """(catalog name, item ids, exact) or None."""
        key = normalise_name(text)
        if len(key) < 4:
            return None
        if key in self._ids:
            return self._display[key], tuple(sorted(self._ids[key])), True
        close = difflib.get_close_matches(key, self._keys, n=2, cutoff=self._cutoff)
        if len(close) != 1:
            return None  # nothing close, or ambiguous
        return self._display[close[0]], tuple(sorted(self._ids[close[0]])), False


SALES_HEADER = "sales list"
PRICE_HEADER = "lowest sale price"
NOT_NAMES = ("item level", "grade", "item")


def locate_rows(image: Image.Image, boxes: Sequence[TextBox]) -> list[RowCells] | None:
    """Split the list into rows and number cells. None when the market list isn't visible."""
    sales = next((b for b in boxes if normalise_name(b.text).startswith(SALES_HEADER)), None)
    price = next((b for b in boxes if normalise_name(b.text).startswith(PRICE_HEADER)), None)
    if sales is None or price is None or price.x <= sales.x:
        return None
    header_bottom = max(sales.bottom, price.bottom)
    grade = next((b for b in boxes if normalise_name(b.text).startswith("grade")), None)
    name_left = grade.left if grade is not None else 0.0
    names = sorted(
        (
            b
            for b in boxes
            if b.top > header_bottom
            and name_left <= b.left
            and b.right < sales.left
            and not normalise_name(b.text).startswith(NOT_NAMES)
        ),
        key=lambda b: b.y,
    )
    if not names:
        return []
    # Row pitch from the gaps between names; one row alone: a multiple of the text height.
    gaps = [b.y - a.y for a, b in zip(names, names[1:], strict=False) if b.y - a.y > a.height]
    pitch = median(gaps) if gaps else 6 * names[0].height
    between = (sales.right + price.left) / 2
    count_left = sales.left - (between - sales.right)
    cells = []
    for box in names:
        # Equipment rows put the name above the row's middle ("Item Level" below it).
        top, bottom = box.y - 0.45 * pitch, box.y + 0.5 * pitch
        if top < 0 or bottom > image.height:
            continue  # cut off by the screen edge
        cells.append(
            RowCells(
                box.text,
                image.crop((round(count_left), round(top), round(between), round(bottom))),
                image.crop((round(between), round(top), image.width, round(bottom))),
            )
        )
    return cells


class MarketReader:
    def __init__(
        self,
        matcher: NameMatcher,
        templates: DigitTemplates | None = None,
        engine: OcrEngine | None = None,
    ) -> None:
        self._matcher = matcher
        self._templates = templates or DigitTemplates.load()
        self._engine = engine

    @property
    def engine(self) -> OcrEngine:
        if self._engine is None:
            self._engine = rapidocr_engine()
        return self._engine

    def read(self, image: Image.Image) -> MarketReading:
        cells = locate_rows(image, self.engine(image))
        if cells is None:
            return MarketReading((), "market list not found (open Market → Exchange and search)")
        heights = [h for c in cells if (h := digit_height(c.price)) is not None]
        usual = median(heights) if heights else None
        rows = []
        for cell in cells:
            match = self._matcher.match(cell.text)
            if match is None:
                continue  # icon badges and other stray text
            name, item_ids, exact = match
            listings = parse_number(self._templates.read(cell.listings))
            price = parse_number(self._templates.read(cell.price))
            height = digit_height(cell.price)
            if usual is not None and height is not None and height < 0.85 * usual:
                price = None  # number clipped by the list's edge
            if not listings or not price:
                price = None  # 0 listings shows "0", which isn't a price; nothing sells for 0
            rows.append(MarketRow(cell.text, name, item_ids, exact, listings, price))
        return MarketReading(tuple(rows))
