# TASKS.md
Development tracker. Owner-only items are marked **(owner)**. Detailed history is in git.

## Current
- [ ] **(owner)** Provide auction house screenshots (English client) at each resolution to support,
      ideally a few searches each, for OCR fixtures

## Next (MVP, in order)
1. [ ] Research spike (game-data-researcher): community recipe databases, data format, craft chances,
       terms of use → decide the recipe source
2. [ ] `calc/`: tier cost, needed crafts, exclusions, tax; tests that reproduce the sheet's totals
3. [ ] Recipe importer → `data/recipes.json` + SQLite schema
4. [ ] OCR spike: RapidOCR vs. Tesseract on the fixtures; decide the engine
5. [ ] OCR pipeline: panel detection across resolutions, row parsing, name matching
6. [ ] Hotkey capture → price_observation
7. [ ] DESIGN.md draft (design-advisor), then the main window: recipe/tier view with prices
8. [ ] Buy vs. craft per tier, profit vs. sell price
9. [ ] Price history view
10. [ ] PyInstaller `.exe` build and README install steps

## Later
- [ ] Automated scan (opt-in, ToS/anti-cheat warning)

## Owner questions (TBD)
- [ ] **(owner)** Weapon WIP sheet: what are column E prices, the "splendant" 1,000,000 line, and the
      final ×2?
- [ ] **(owner)** Why are two Legendary materials excluded from the sum?
- [ ] **(owner)** Default buy/sell tax rates (10% each?)

## Bugs
None open.

## Done
- [x] Project setup: docs in `brain/`, agents, tooling (2026-10-05)
