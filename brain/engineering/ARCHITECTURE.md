# ARCHITECTURE.md
How the app works. What it must do is in `../product/REQUIREMENTS.md`.
Status: planned. Nothing below is built yet; update this file as code lands.

## Stack
- Python 3.13, PySide6 (Qt) for the UI.
- SQLite (stdlib `sqlite3`) for prices, history and recipes.
- OCR: OpenCV for preprocessing + an OCR engine, **TBD**: RapidOCR (pip-only, no system install,
  easiest to ship) vs. Tesseract (needs its own installer). Decide by benchmarking on fixture
  screenshots.
- Packaging: PyInstaller, one-folder `.exe` build.
- Dev: pytest, ruff (lint + format), mypy.

## Components (`src/aion2calc/`)
| Package | Responsibility |
|---|---|
| `app.py` | Entry point; builds the Qt app and main window. |
| `ui/` | Recipe/tier view (the sheet's blocks), prices, history, settings. No business logic. |
| `capture/` | Global hotkey; grabs the game window or screen region. Later: automated scan. |
| `ocr/` | Locate the listing area, preprocess, run OCR, parse rows, match names to known items. |
| `data/` | SQLite store and the recipe importer/scraper. |
| `calc/` | Pure functions: tier cost, needed crafts, exclusions, buy-vs-craft, profit, tax. |

`calc/` and the parsing parts of `ocr/` are pure and unit-tested; `ui/` and `capture/` stay thin.

## Data flow
```
hotkey → capture (screenshot) → ocr (rows: name, unit price, qty)
       → match name to item id (fuzzy, against recipe item names)
       → data: insert price_observation
calc reads latest prices + recipes + user overrides → ui shows tiers, totals, profit
```

## Storage (SQLite, planned)
- `item(id, name, grade, tradable)`
- `recipe(id, output_item_id, tier, output_qty, base_chance)` and
  `recipe_material(recipe_id, item_id, qty)`
- `price_observation(item_id, unit_price, qty, observed_at, source)`; source = `ocr` or `manual`
- `user_setting` / overrides: per-material price override and exclusion, per-tier chance override,
  buy/sell tax.

The database lives in the user's app-data folder (`%LOCALAPPDATA%\Aion2CraftingCalculator\`), not
next to the `.exe`.

## OCR across resolutions
- Never hard-code pixel coordinates. Find the listing panel relative to anchors (template matching on
  stable UI elements) and scale to a reference size before OCR.
- Fixture screenshots per resolution in `tests/fixtures/`, each with expected rows, drive the tests.
- Name matching: OCR text is fuzzy-matched to known item names; low-confidence matches are flagged,
  not silently stored.

## Recipe data
- Source **TBD** (see REQUIREMENTS Open decisions). The importer writes a normalized
  `data/recipes.json` that ships with the app and loads into SQLite; scraping is a dev-time step, not
  something end users run.

### Source research (2026-10-05, unverified details marked)
- **No official or public API** has Global item, recipe or market data. NCSoft's public web API
  (wrapped by `nuriland/aion2-api`) covers characters, rankings and news only.
- **aion2hub.com / aion2hub.me:** about 1000+ recipe pages (`/tools/crafting-calculator/<slug>-<id>`),
  direct materials plus the full chain. No craft chance shown. HTML only; robots.txt disallows
  `/api/` on .com. May mix KR/TW-only items. No terms page found.
- **gamers4.life:** 2,442 recipes; recipe pages show success %, critical % and fail reward
  (confirmed on conversion recipes, not yet on equipment). robots.txt disallows `/api/`, `/_next/`.
  Has Terms pages (not yet read).
- **metabot.gg:** documents that craft success is a curve by proficiency (your level minus the
  recipe's): about 67.5–95.2% at level, up to 99.2% over-levelled; combo (proc one grade higher) on
  some recipes. Cross-check only; no export.
- **Inven (KR):** unofficial JSON at `aion2.inven.co.kr/db/api/craft/getList` (used by
  `dodsas/aion2`): `code`, `product_code`, `combo_product_code`, `combo_probability`, materials with
  `count`. Korean names; terms unchecked.
- **Tier relationship (partly confirmed):** higher grades consume the lower-grade item (e.g.
  Artisan's necklace needs Expert's necklace ×1). The sheet's 64/16/4/1 counts are not yet explained.
- **Prices:** no source publishes Global market prices; OCR stays the price source.
- **FaHaDoF69/aion2:** C#/OpenCV template matching, no data shipped, licence forbids reuse beyond
  learning. Reference for approach only.

## Constraints and risks
- **Game ToS / anti-cheat:** hotkey capture only reads the screen. The later automated scan sends
  input to the game and must be opt-in with a warning.
- No network calls at runtime except, possibly, a future recipe-data update (TBD).
