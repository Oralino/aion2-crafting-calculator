# CLAUDE.md
Permanent instructions for Claude Code in this repository: a Windows desktop app (Python + PySide6)
that calculates Aion 2 crafting costs, with prices read from the in-game auction house by OCR. Shared
with friends as a packaged `.exe`. Solo project.

## Documents
Project knowledge lives in `brain/`, one folder per question: `product/` (what it does), `design/`
(how it looks), `engineering/` (how it works), `work/` (what's being done). Only `CLAUDE.md` and
`README.md` stay in the root.

| File | Owns | Maintained by |
|---|---|---|
| `CLAUDE.md` | Rules, commands, workflow | main session |
| `brain/product/REQUIREMENTS.md` | Goal, calculation rules, features, owner decisions, scope, acceptance criteria | main session |
| `brain/engineering/ARCHITECTURE.md` | Stack, components, data flow, storage, OCR approach, risks | main session |
| `brain/design/DESIGN.md` | How it looks | design-advisor (owner approves) |
| `brain/work/TASKS.md` | Current, next, later work, owner questions, bugs | main session |
| `brain/work/HANDOFF.md` | Session handoff, only when one is written (local, never committed) | main session |
| `README.md` | Install, usage, build | main session |

One fact lives in one file; link instead of repeating. Update the docs when the code changes, and flag
contradictions between docs and code instead of guessing. Unresolved items are marked **TBD**.

## Commands
Run from the repo root. Use the venv's Python (`.venv\Scripts\python`); in Git Bash use
`.venv/Scripts/python`.
```bash
python -m venv .venv                         # once
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m aion2calc.app        # run the app
.venv/Scripts/python -m pytest               # tests
.venv/Scripts/python -m ruff check .         # lint   (ruff check --fix . to autofix)
.venv/Scripts/python -m ruff format --check . # format check (ruff format . to apply)
.venv/Scripts/python -m mypy                 # type check (strict)
.venv/Scripts/python tools/import_recipes.py # rebuild data/recipes.json from aion2hub (~30 min
                                             # uncached; --limit N to try a few pages)
```
**Check** = pytest + ruff check + ruff format --check + mypy; must pass before every commit.
```bash
.venv/Scripts/python -m PyInstaller aion2calc.spec --noconfirm --clean   # build the .exe
```
Output: `dist/Aion2CraftingCalculator/` (one folder; zip it to share). Run Bash from the repo root,
never `cd` into `dist/`: an open working folder there blocks the next build's cleanup.

## Conventions
- Python 3.13, type hints everywhere (mypy strict), ruff for lint and format, line length 100.
- `src/` layout; package `aion2calc`. Pure logic (`calc/`, OCR parsing) has no Qt imports and is
  unit-tested; `ui/` and `capture/` stay thin. Tests in `tests/`, OCR fixture screenshots in
  `tests/fixtures/`.
- Money is Kinah as `int`; craft chances and tax as `float`/`Decimal` only where needed. Never round
  intermediate values; round only for display.
- OCR: never hard-code pixel coordinates; everything must work across resolutions
  (see `ARCHITECTURE.md`).
- Never add automation that sends input to the game outside the opt-in automated-scan feature.
- Add a dependency only with a clear reason, and record why in `ARCHITECTURE.md`.
- Comment only what isn't obvious. Never invent features, metrics or game data.

## Models and agents
- **Opus (the main session)** writes and approves all production code, and makes architecture
  decisions, debugs hard problems and does refactors.
- Agents (general ones live in `~/.claude/agents/`; project ones in `.claude/agents/`):
  - `code-reviewer` (Sonnet, read-only): correctness, maintainability, performance, accessibility.
  - `qa-checker` (Haiku, Bash for checks only): runs Check and the build, mechanical searches.
  - `design-advisor` (Opus, edits only `brain/design/DESIGN.md`): drafts DESIGN.md, new visual
    patterns and design deviations.
  - `game-data-researcher` (Sonnet, read-only + web, project agent): evaluates game data sources
    (recipes, craft chances, market data) and their terms of use.
- Reviewer and QA **only report**; the main session judges their findings and makes the changes.
  Never two agents writing the same file. Give each agent only the files its job needs, and run agents
  in parallel only when their work is independent.

## When to use agents
Before a task, classify it and state the recommended effort in one line (the owner sets effort; switch
only at task boundaries, and if a "small" task grows, stop and say so):

| Tier | Examples | Agents | Effort |
|---|---|---|---|
| Small | Text, rename, one config value, one-file fix | none; run Check | low/medium |
| Medium | New component or feature, behaviour or state change, multi-file refactor | code-reviewer | medium |
| Large / high-risk | OCR pipeline, capture/automation, storage schema, scraper, packaging, many files | code-reviewer + qa-checker | high |
| Milestone / release | Before sharing a new `.exe` | code-reviewer + qa-checker | high |

design-advisor runs only for DESIGN.md and new visual patterns.

## Secrets and privacy
- No API keys are needed. Never commit `.env`, keys, or the user database (`.gitignore` covers them).
- Nothing personal in the repo: no character names, account info or real names in fixtures or
  screenshots.
- Commit identity for this repo is `Oralino` with the GitHub no-reply address (local git config).
  Never use the owner's real name or personal email.

## Git
- Work on `main` locally; GitHub remote TBD (added when the app is shared).
- Commit after each completed task, once its tier's checks have passed, not before. Only the main
  session commits; agents never commit or push.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`), one logical change
  per commit.
- Never commit secrets. If the working tree has unrelated changes, ask before committing.
- Never push or force-push without asking first.
