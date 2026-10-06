# TASKS.md
Development tracker. Owner-only items are marked **(owner)**. Detailed history is in git.

## Current

## Next (MVP, in order)
1. [x] Research spike: recipe sources → aion2hub HTML (findings in ARCHITECTURE.md)
2. [x] `calc/`: tier cost, needed crafts, exclusions, buy tax; tests reproduce the sheet's Accessories totals
3. [x] Recipe importer → `data/recipes.json` (SQLite moves to the price task: it only holds prices,
       history and overrides)
4. [x] OCR spike: RapidOCR for names + digit template matching for numbers, verified on 5 market
       captures at 3440×1440 and 1920×1080 (results in ARCHITECTURE.md)
5. [x] OCR pipeline: panel detection across resolutions, row parsing, name matching
6. [x] F10 capture → SQLite price store → calculator (owner live-tested 2026-10-05; needs admin)
7. [x] DESIGN.md (approved) and the main window: recipe search, tier blocks, summary with profit,
       settings (taxes)
8. [ ] Buy vs. craft per tier, profit vs. sell price
9. [ ] Price history view
10. [x] PyInstaller `.exe` build (runs as administrator) and README install steps
11. [ ] **(owner)** Test the `.exe` from the v0.1.0 GitHub pre-release: start it, open a recipe,
        F10 in game; then mark the release as a full release

## OCR hardening (from the 2026-10-05 review, not yet done)
- [ ] Flag a captured price far from the item's previous one (a single misread digit) instead of
      storing it silently
- [ ] Clipped-number check fails when only one row is visible (it compares rows with each other);
      compare with the name's text height instead, and check the listings cell too
- [ ] Bound the price crop at the list's right edge (now it runs to the screen edge)
- [ ] Test capture on a 125%/150% Windows display scale

## UI follow-ups
- [ ] Save per-recipe inputs (chances, combo rates, planned crafts, exclusions, sell prices);
      manual material prices are already saved
- [ ] Recipe picker: grade colours and match highlighting in the popup
- [ ] A rejected price edit closes the editor and drops what was typed; keep it open, marked invalid
- [ ] Prices tab (price history), once capture exists

## Later
- [ ] Automated scan (opt-in, ToS/anti-cheat warning)
      Finding (2026-10-05): the game ignored simulated mouse clicks and key presses (Windows input
      injection), likely blocked by anti-cheat. Automated scan probably isn't feasible this way.
- [ ] Proficiency-based craft chance (success curve by crafting level vs. recipe level)

## Owner questions (TBD)

## Bugs
None open.

## Done
- [x] Project setup: docs in `brain/`, agents, tooling (2026-10-05)
- [x] Bundled fonts Inter + JetBrains Mono (2026-10-05)
- [x] Recipe search: words in any order, dropdown as you type (2026-10-05)
- [x] Planned crafts per tier, valued Splendent piece, Combos per tier (2026-10-05)
