# Aion2 Crafting Calculator

A Windows desktop app that works out what an Aion 2 (Global) craft really costs and whether it's
worth doing. It reads auction house prices from your screen with OCR.

**Status:** early development; not usable yet.

## Development
Requires Python 3.13 on Windows.
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m aion2calc.app
```
Tests and checks are listed in `CLAUDE.md` (Commands).

## Note
Hotkey capture only reads your screen. A future automated-scan mode would send input to the game,
which may break the game's terms of service; it will be opt-in.
