"""Market reader against the owner's captures (tests/fixtures/market). Runs real OCR: slower."""

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from aion2calc.app import RECIPES
from aion2calc.data.recipes import Catalog
from aion2calc.ocr.digits import DigitTemplates, parse_number
from aion2calc.ocr.market import (
    MarketReader,
    MarketReading,
    MarketRow,
    NameMatcher,
    OcrEngine,
    TextBox,
    locate_rows,
    normalise_name,
    rapidocr_engine,
)

FIXTURES = Path(__file__).parent / "fixtures" / "market"
CAPTURES = sorted(p.stem for p in FIXTURES.glob("*.json"))


def expected(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data


def image(name: str) -> Image.Image:
    return Image.open(FIXTURES / f"{name}.png")


@pytest.fixture(scope="module")
def engine() -> OcrEngine:
    return rapidocr_engine()


@pytest.fixture(scope="module")
def matcher() -> NameMatcher:
    catalog = Catalog.load(RECIPES)
    return NameMatcher({i: item.name for i, item in catalog.items.items()})


@pytest.mark.parametrize("capture", CAPTURES)
def test_reads_every_capture(capture: str, engine: OcrEngine, matcher: NameMatcher) -> None:
    reading = MarketReader(matcher, engine=engine).read(image(capture))
    assert reading.problem is None
    got = {normalise_name(r.name or ""): (r.listings, r.price) for r in reading.rows}
    for row in expected(capture)["rows"]:
        key = normalise_name(row["name"])
        listings = row["listings"] or None  # 0 listings reads as no number
        assert got[key] == (listings, row["lowest_price"]), row["name"]
    for partial in expected(capture).get("partial_rows", []):
        assert got.get(normalise_name(partial), (None, None))[1] is None


@pytest.mark.parametrize("held_out", CAPTURES)
def test_digits_generalise_to_an_unseen_capture(held_out: str, engine: OcrEngine) -> None:
    """Learn digit shapes from the other captures only, then read this one."""
    templates = DigitTemplates()
    for capture in CAPTURES:
        if capture == held_out:
            continue
        rows = {normalise_name(r["name"]): r for r in expected(capture)["rows"]}
        for cell in locate_rows(image(capture), engine(image(capture))) or []:
            row = rows.get(normalise_name(cell.text))
            if row and row["listings"]:
                templates.learn(cell.listings, str(row["listings"]))
                templates.learn(cell.price, f"{row['lowest_price']:,}")
    if not templates.complete:
        pytest.skip("the other captures don't show every digit")
    rows = {normalise_name(r["name"]): r for r in expected(held_out)["rows"]}
    for cell in locate_rows(image(held_out), engine(image(held_out))) or []:
        row = rows.get(normalise_name(cell.text))
        if row and row["listings"]:
            assert parse_number(templates.read(cell.price)) == row["lowest_price"], row["name"]
            assert parse_number(templates.read(cell.listings)) == row["listings"], row["name"]


def test_screen_without_the_market_is_reported(matcher: NameMatcher) -> None:
    def no_text(_: Image.Image) -> list[TextBox]:
        return [TextBox("Mosslan Forest", 10, 10, 200, 30)]

    reading = MarketReader(matcher, engine=no_text).read(Image.new("RGB", (800, 600)))
    assert reading.problem is not None
    assert reading.rows == ()


def test_name_matching() -> None:
    m = NameMatcher({1: "Refining Stone", 2: "Refining Stone", 3: "Expert's Refining Stone"})
    assert m.match("Refining Stone") == ("Refining Stone", (1, 2), True)
    assert m.match("Expert’s Refining  Stone") == ("Expert's Refining Stone", (3,), True)
    assert m.match("Experts Refining Stone") == ("Expert's Refining Stone", (3,), False)
    assert m.match("a") is None
    assert m.match("Mosslan Forest") is None


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("3999", 3999),
        ("1,850,000", 1_850_000),
        ("0", 0),
        ("", None),
        ("1,85,000", None),
        ("12,3", None),
        ("066,666", None),  # leading zero: a misread
        ("1850000", None),  # 10,000 and up always has commas
    ],
)
def test_parse_number(text: str, value: int | None) -> None:
    assert parse_number(text) == value


def test_unclear_digits_read_as_nothing() -> None:
    templates = DigitTemplates.load()
    blob = Image.new("RGB", (60, 30))
    blob.paste((255, 255, 255), (5, 5, 50, 25))  # one wide white block, not a digit
    assert templates.read(blob) == ""


def test_incomplete_templates_are_refused(tmp_path: Path) -> None:
    partial = DigitTemplates({d: s for d, s in DigitTemplates.load().samples.items() if d != "7"})
    partial.save(tmp_path / "t.npz")
    with pytest.raises(ValueError, match="7"):
        DigitTemplates.load(tmp_path / "t.npz")


def test_approximate_names_and_missing_prices_are_not_stored() -> None:
    exact = MarketRow("Odyle", "Odyle", (1,), True, 3, 900)
    fuzzy = MarketRow("Experts Stone", "Expert's Stone", (2,), False, 3, 900)
    unread = MarketRow("Ruby", "Ruby", (3,), True, 3, None)
    reading = MarketReading((exact, fuzzy, unread))
    assert reading.priced == (exact,)
    assert reading.approximate == (fuzzy,)
