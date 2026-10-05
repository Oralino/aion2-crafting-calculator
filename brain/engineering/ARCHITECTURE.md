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

## Constraints and risks
- **Game ToS / anti-cheat:** hotkey capture only reads the screen. The later automated scan sends
  input to the game and must be opt-in with a warning.
- No network calls at runtime except, possibly, a future recipe-data update (TBD).
