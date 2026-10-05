"""Dev tool: rebuild data/recipes.json from aion2hub.com crafting-calculator pages.

Fetches the sitemap, then every recipe page, one request per second, caching pages in
.cache/aion2hub/ so reruns only fetch what's missing (delete the folder to refresh). Only public
HTML pages are read; aion2hub's robots.txt disallows /api/, which this never touches.

    .venv/Scripts/python tools/import_recipes.py [--limit N]
"""

import argparse
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from aion2calc.data.aion2hub import ParseError, RecipePage, parse_recipe_page
from aion2calc.data.recipes import build_catalog

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "aion2hub"
OUTPUT = ROOT / "data" / "recipes.json"
SITE = "https://aion2hub.com"
RECIPE_URL = re.compile(rf"<loc>{SITE}/tools/crafting-calculator/([a-z0-9-]+-(\d+))</loc>")
USER_AGENT = "Aion2CraftingCalculator/0.1 (personal recipe import; 1 request/second)"
DELAY_SECONDS = 1.0
MAX_FETCH_ERRORS_IN_A_ROW = 5

_last_request = 0.0


def fetch(url: str) -> str:
    global _last_request
    wait = _last_request + DELAY_SECONDS - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text: str = response.read().decode("utf-8")
    finally:
        _last_request = time.monotonic()  # throttle after failures too
    return text


def write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def load_page(slug: str, item_id: int) -> RecipePage:
    """Parse a recipe page, from the cache when possible. Only pages that parse are cached, so a
    truncated download or an error page is fetched again next time."""
    path = CACHE / f"{slug}.html"
    if path.exists():
        try:
            return parse_recipe_page(path.read_text(encoding="utf-8"), item_id)
        except ParseError:
            pass  # cached by an older parser or damaged; fetch again
    html = fetch(f"{SITE}/tools/crafting-calculator/{slug}")
    page = parse_recipe_page(html, item_id)
    write_atomic(path, html)
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild data/recipes.json from aion2hub.com.")
    parser.add_argument("--limit", type=int, help="only the first N recipe pages (for testing)")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="where to write the JSON")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="write the output even with --limit or failed pages",
    )
    args = parser.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    sitemap = fetch(f"{SITE}/sitemap.xml")  # always fresh, so new recipes are picked up
    slugs = RECIPE_URL.findall(sitemap)
    if not slugs:
        print("no recipe pages in the sitemap; has its format changed?", file=sys.stderr)
        return 1
    if args.limit is not None:
        slugs = slugs[: max(args.limit, 0)]
    print(f"{len(slugs)} recipe pages", flush=True)

    pages: list[RecipePage] = []
    failures: list[str] = []
    fetch_errors_in_a_row = 0
    for n, (slug, item_id) in enumerate(slugs, 1):
        try:
            pages.append(load_page(slug, int(item_id)))
            fetch_errors_in_a_row = 0
        except ParseError as error:
            failures.append(f"{slug}: {error}")
        except (OSError, urllib.error.URLError, UnicodeDecodeError) as error:
            failures.append(f"{slug}: {error}")
            fetch_errors_in_a_row += 1
            if fetch_errors_in_a_row >= MAX_FETCH_ERRORS_IN_A_ROW:
                print(f"stopping: {fetch_errors_in_a_row} fetch errors in a row", file=sys.stderr)
                break
        if n % 100 == 0:
            print(f"  {n}/{len(slugs)}", flush=True)

    catalog, warnings = build_catalog(pages)
    combos = sum(1 for r in catalog.recipes.values() if r.combo_item_id)
    print(f"{len(catalog.recipes)} recipes, {combos} with combo, {len(failures)} failed pages")
    for line in warnings:
        print(f"warning: {line}")
    for line in failures:
        print(f"failed: {line}")

    partial = args.limit is not None or bool(failures)
    if partial and not args.allow_partial:
        print(f"not writing {args.output}: partial run (use --allow-partial)", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(args.output, catalog.to_json())
    print(f"wrote {args.output}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
