# ARCHITECTURE.md
How the app works. What it must do is in `../product/REQUIREMENTS.md`.
Status: built so far: `calc/`, `data/` (recipe import), `session.py` and the main window in `ui/`.
Capture, OCR and the SQLite store are planned; update this file as code lands.

## Stack
- Python 3.13, PySide6 (Qt) for the UI.
- SQLite (stdlib `sqlite3`) for prices, history and overrides (recipes are JSON, see Storage).
- OCR: **RapidOCR** (`rapidocr` + `onnxruntime`, Apache-2.0 / MIT) with its English PP-OCRv5 mobile
  recognition model; OpenCV (headless build) for preprocessing. Chosen in the OCR spike (below);
  to be confirmed on auction house screenshots.
- Fonts: Inter 4.1 (Regular/Medium/SemiBold) and JetBrains Mono 2.304 (Regular/SemiBold) static
  TTFs in `src/aion2calc/ui/fonts/` with their OFL 1.1 licence files, registered at startup
  (`theme.load_fonts`); downloaded from the projects' GitHub releases (owner OK, 2026-10-05).
  Segoe UI / Consolas are fallbacks. The licence files must ship with the `.exe`.
- Packaging: PyInstaller, one-folder `.exe` build.
- Dev: pytest, ruff (lint + format), mypy.

## Components (`src/aion2calc/`)
| Package | Responsibility |
|---|---|
| `app.py` | Entry point; applies the theme, loads `data/recipes.json` and settings, opens the window. |
| `session.py` | The open craft (Qt-free): a recipe chain plus the user's prices, chances, combo rates, exclusions and sell price, validated, turned into `calc` objects. Combo items made by the tier below are CRAFTED (cost 0). |
| `ui/` | Widgets only, reading and editing a `CraftSession`: `theme.py` (all design tokens, QPalette and generated QSS), `format.py` (number display/parsing), `tier_block.py` (tier header + material table model and delegates), `summary.py`, `recipe_search.py`, `settings_page.py`, `settings_store.py` (QSettings, validated on load), `main_window.py`. |
| `capture/` | Global hotkey; grabs the game window or screen region. Later: automated scan. |
| `ocr/` | Locate the listing area, preprocess, run OCR, parse rows, match names to known items. |
| `data/` | aion2hub page parser (`aion2hub.py`), recipe catalog and tier chains (`recipes.py`); later the SQLite store. |
| `calc/` | Pure functions: combo-chain tier cost, needed crafts, lost value, exclusions, tax; later buy-vs-craft and profit. |

Dev tools live in `tools/` and aren't shipped: `tools/import_recipes.py` rebuilds `data/recipes.json`.

`calc/` and the parsing parts of `ocr/` are pure and unit-tested; `ui/` and `capture/` stay thin.

## Data flow
```
hotkey → capture (screenshot) → ocr (rows: name, unit price, qty)
       → match name to item id (fuzzy, against recipe item names)
       → data: insert price_observation
calc reads latest prices + recipes + user overrides → ui shows tiers, totals, profit
```

## Storage (SQLite, planned)
Recipes and items are **not** in SQLite: they're read-only game data, about 1,700 recipes, loaded from
`data/recipes.json` into memory (see Recipe data). SQLite holds what the user creates:
- `price_observation(item_id, unit_price, qty, observed_at, source)`; source = `ocr` or `manual`
- per-recipe inputs: chances, combo rates, exclusions, sell price (until then they live only in the
  open `CraftSession`; manual prices carry over between recipes in one run).

Buy/sell tax are already remembered via `QSettings` (Windows registry,
`HKCU\Software\Aion2CraftingCalculator`).

The database lives in the user's app-data folder (`%LOCALAPPDATA%\Aion2CraftingCalculator\`), not
next to the `.exe`.

## OCR across resolutions
- Never hard-code pixel coordinates. Find the listing panel relative to anchors (template matching on
  stable UI elements) and scale to a reference size before OCR.
- Fixture screenshots per resolution in `tests/fixtures/`, each with expected rows, drive the tests.
- Name matching: OCR text is fuzzy-matched to known item names; low-confidence matches are flagged,
  not silently stored.

### OCR spike (2026-10-05)
Run on the owner's 4 crafting-window screenshots (same game font as the auction house; no AH
screenshots yet), scoring 58 hand-checked strings: item names, `195/4`-style counts, levels, stats,
and `1,428` / `25,320` with thousands separators.
| Engine | Score | Time per full screenshot | Notes |
|---|---|---|---|
| RapidOCR, default (Chinese+English) model | 56/58 | 0.8 s | Icons read as stray CJK characters |
| **RapidOCR, English PP-OCRv5 mobile** | **55/58** | **0.75 s** | No stray characters; 7.9 MB model |
| Windows built-in OCR (`Windows.Media.Ocr`) | 39/58 (50/58 at 2× upscale) | 0.05–0.12 s | Misses many numbers (`1,428`, `0/14`, `25,320`) |
- Every RapidOCR miss was a scoring artefact: `Lv.25` read without the space, and text the tooltip
  hides on screen. Treat all of them as reads of visible text.
- **Risk for the AH:** neighbouring numbers merge (`161 ▾197` → `161197`). Read the price and quantity
  columns as separate crops, never a whole row at once.
- Small fixes to plan for: `l`/`i` confusion in prose (`materlals`), optional spaces (`Lv.25`).
  Prices are digits and commas only, so parse with a strict pattern and reject anything else.
- Size: rapidocr 32 MB (most of it optional models; we need ~18 MB), onnxruntime 46 MB, OpenCV
  113 MB (the headless build is smaller). Packaging should exclude unused models.
- Tesseract not tested: it needs its own installer, which the shared `.exe` should avoid.

### Market screen findings (2026-10-05, owner's 3440×1440 captures)
- The price source is **Market → Exchange → Main**: a search lists one row per matching item with
  Grade, Item name, **Sales List** (number of listings) and **Lowest Sale Price** (a coin icon,
  then the number). One search prices several materials (e.g. all four Refining Stone grades).
  The header also shows "Current Tax Rate 10%".
- Prices under 10,000 have no thousands separator (`3999`, `6999`); larger ones do (`1,850,000`).
- **RapidOCR misreads this font's digits with full confidence**: `3999` → `666`, `6999` → `6669`,
  `999,990` → `066'666`, even with column crops. Item names were always read correctly.
- **Digit template matching reads every number correctly**: white glyphs are segmented by column
  (the gold coin icon is taller and dropped; a short glyph between digits is a comma), each digit
  normalised to 12×18 and matched to templates learned from known captures. Learned from two
  captures, it read an unseen third (`999,990`, `249,998`, `1,850,000`, counts) with no errors.
- **Decision:** RapidOCR for item names; glyph template matching for prices and listing counts.
  Templates ship with the app.
- **Verified across resolutions:** templates learned only from 3440×1440 captures read a 1920×1080
  windowed capture (text ~25% smaller) with no errors.
- **Layout is found, not hard-coded:** columns come from the OCR'd header labels ("Sales List",
  "Lowest Sale Price"), rows from the item-name boxes. The panel's position and width change with
  the window's aspect ratio (21:9 vs 16:9), so fixed coordinates would not work.
- **Equipment rows** add an "Item Level N" line under the name (skip it). **Rows with 0 listings**
  are dimmed and show price 0: the dim digits fail the white-text test, so they yield no price,
  never 0 Kinah. A row cut off by scrolling also yields no price. Item-icon badges OCR as stray
  short text ("a"); names are kept only when they match the recipe catalog.
- Test captures: `tests/fixtures/market/*_3440x1440.png` (listings panel crops only, no personal
  information) with the expected rows in matching `.json` files.
## Recipe data
- **Source:** aion2hub.com crafting-calculator pages (owner decision). `tools/import_recipes.py`
  reads the sitemap, fetches each page at 1 request/second with an identifying user agent, caches
  pages in `.cache/aion2hub/` (gitignored), and writes `data/recipes.json`, which ships with the app.
  Never touches `/api/` (disallowed by robots.txt). Scraping is a dev-time step, not something end
  users run.
- **Page format:** Next.js React Server Components payload embedded in the HTML. Rows are
  `<hex id>:<json>\n`, except text rows `<id>:T<hex byte length>,<text>` which are length-prefixed
  and followed directly by the next row, and hint rows with an empty id. The parser walks the element
  tree (`["$", tag, key, props]`, `"$L<id>"` references) rather than rendered HTML. Each page gives:
  name, grade, profession, mastery level (optional), direct components (item id, name, qty) and a
  "KR/TW" badge when the recipe is only known from Korea/Taiwan client data.
- **Combo pairing:** aion2hub has a page for each combo item too (e.g. Splendent Ruby Necklace),
  repeating the recipe that combos into it, but doesn't link the two. Pages with the same profession,
  mastery and components are one recipe: the lowest grade is the normal result, the next grade the
  combo result. Each faction (Elyos/Asmodian) has its own item ids, paired in id order. Groups that
  don't fit (more than two grades, uneven counts) are reported as warnings, not guessed.
  Pairing goes by name (the combo name keeps every word of the normal one), grade only as a sanity
  check, since the top tier's two items share a grade. A second pass pairs "Splendent <name>" with
  "<name>" even when aion2hub shows the Splendent with a different, smaller recipe (e.g. Splendent
  Dark Dragon Lord Boots); in game it's the combo result (owner), so that page's recipe is dropped.
- **Tier chains:** a recipe that uses a combo item as a component is the next tier of the recipe
  that combos into it (Star Dragon Lord ← Artisan's ← Expert's ← base), confirmed against the
  owner's in-game screenshots of the Ruby Necklace chain (2026-10-05).
- **`recipes.json` format** (versioned, `"format": 1`): `items` (id → name, grade) and `recipes`
  (item, profession, mastery, ingredients `[[item_id, qty]]`, combo item id, `kr_tw_only`).
- KR/TW-only recipes are kept but flagged; the UI hides them by default (Global only).

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
