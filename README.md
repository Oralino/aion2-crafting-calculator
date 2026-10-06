# Aion2 Crafting Calculator

A Windows desktop app for AION 2 (Global) that works out what a craft really costs and whether it's
worth doing. It reads auction house (Market) prices straight from your screen.

**Status:** in development. The calculator and market capture work.

## Install
1. Download the latest `Aion2CraftingCalculator-…-windows.zip` from
   [Releases](https://github.com/Oralino/aion2-crafting-calculator/releases) and unzip it anywhere
   (keep everything in the folder together).
2. Run `Aion2CraftingCalculator.exe`. Windows asks for administrator rights: AION 2 runs as
   administrator, and Windows only passes the F10 key to an app that does too. Windows
   SmartScreen may warn about an unknown app (it isn't signed); choose "More info" → "Run anyway".

No Python or internet connection needed.

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
`%LOCALAPPDATA%\Aion2CraftingCalculator\prices.sqlite3` (with `error.log` there if something goes
wrong). If you approve the administrator prompt with a different Windows account, that account's
folder is used instead. The app sends nothing anywhere.

The app never sends input to the game.

## Development
Requires Python 3.13 on Windows.
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m aion2calc.app
```
For F10 to work while the game has focus, run it from a terminal opened as administrator.

Build the `.exe` (run the tests once first, so RapidOCR's models are downloaded to bundle):
```bash
.venv/Scripts/python -m PyInstaller aion2calc.spec --noconfirm --clean
```
The app is in `dist/Aion2CraftingCalculator/`; zip that whole folder to share it.

Tests, checks and dev tools are listed in `CLAUDE.md` (Commands). Project docs live in `brain/`.

## Credits
- OCR: [RapidOCR](https://github.com/RapidAI/RapidOCR) (Apache-2.0).
- Fonts: [Inter](https://github.com/rsms/inter) and
  [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono), SIL Open Font License 1.1
  (licence files in `src/aion2calc/ui/fonts/`).

AION 2 is a trademark of NCSOFT. This is an unofficial fan tool, not affiliated with NCSOFT.
