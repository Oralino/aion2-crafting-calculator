"""Dev tool: learn the market font's digit shapes from the test captures and save them.

Reads every tests/fixtures/market/*.png with its .json (expected rows), finds the rows like the
app does, and learns each listings/price cell from its known value. Writes
src/aion2calc/ocr/digit_templates.npz, which ships with the app.

    .venv/Scripts/python tools/build_digit_templates.py
"""

import json
import sys
from pathlib import Path

from PIL import Image

from aion2calc.ocr.digits import TEMPLATES, DigitTemplates
from aion2calc.ocr.market import locate_rows, normalise_name, rapidocr_engine

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "market"


def main() -> int:
    engine = rapidocr_engine()
    templates = DigitTemplates()
    for json_path in sorted(FIXTURES.glob("*.json")):
        expected = {
            normalise_name(r["name"]): r
            for r in json.loads(json_path.read_text(encoding="utf-8"))["rows"]
        }
        image = Image.open(json_path.with_suffix(".png"))
        cells = locate_rows(image, engine(image)) or []
        learned = 0
        for cell in cells:
            row = expected.get(normalise_name(cell.text))
            if row is None or not row["listings"]:
                continue
            templates.learn(cell.listings, str(row["listings"]))
            templates.learn(cell.price, f"{row['lowest_price']:,}")
            learned += 1
        print(f"{json_path.stem}: learned {learned} rows")
    if not templates.complete:
        missing = sorted(set("0123456789") - set(templates.samples))
        print(f"missing digits {missing}; add a capture that shows them", file=sys.stderr)
        return 1
    templates.save(TEMPLATES)
    print(f"wrote {TEMPLATES} ({sum(len(v) for v in templates.samples.values())} glyphs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
