# Aion2 Crafting Calculator

A Windows desktop app for AION 2 (Global) that works out what a craft really costs and whether it's
worth doing. It reads auction house (Market) prices straight from your screen.

**Status:** in development. The calculator works; the market capture is being tested.

## What it does
- **Every craftable recipe** (weapons, armour, accessories) with its full combo chain, e.g.
  Ruby Necklace → Expert's → Artisan's → Star Dragon Lord Necklace.
- **Real crafting maths:** your in-game success chance per tier and the 25% combo chance
  needed to reach the next tier. Failed crafts use up the item from the tier below, so the
  lower tiers need more crafts than a simple 64/16/4/1.
- **Total cost and "lost" value:** what the failed and non-combo crafts cost you.
- **Profit:** sell price minus total cost after the 10% market tax, counting the 25% chance
  of the Splendent version at the top tier.
- **Market capture (F10):** open Market → Exchange in the game, search, press F10. The app
  reads every listed item's lowest price and fills it in. You can override any price by hand.

## Privacy
Capture only reads the AION 2 window, only when it's the active window, and only when you press
F10. Screenshots are never saved. Prices are stored locally in
`%LOCALAPPDATA%\Aion2CraftingCalculator\prices.sqlite3`. The app sends nothing anywhere.

The app never sends input to the game.

## Development
Requires Python 3.13 on Windows.
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m aion2calc.app
```
Tests, checks and dev tools are listed in `CLAUDE.md` (Commands). Project docs live in `brain/`.

## Credits
- Recipe data from [aion2hub.com](https://aion2hub.com).
- OCR: [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache-2.0).
- Fonts: [Inter](https://github.com/rsms/inter) and
  [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono), SIL Open Font License 1.1
  (licence files in `src/aion2calc/ui/fonts/`).

AION 2 is a trademark of NCSOFT. This is an unofficial fan tool, not affiliated with NCSOFT.
