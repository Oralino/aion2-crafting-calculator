# DESIGN.md
Visual source of truth, maintained by design-advisor. **Status: approved by the owner
(2026-10-05).** Calculation rules and features live in `../product/REQUIREMENTS.md`; stack in
`../engineering/ARCHITECTURE.md`.

Visual identity adapted from the designmd.app library entry "FinTech Plataforma Financeira"
(<https://designmd.app/en/library/fintech-plataforma-financeira>): dark surfaces, soft gold accent,
Inter + JetBrains Mono, 8px grid. Everything landing-page specific (hero, navbar, CTA, pricing,
testimonials, breakpoints, decorative charts) is dropped; this is a dense desktop tool.

## Known constraints
- PySide6 desktop app on Windows; used alongside the game (often on a second monitor or alt-tabbed).
- Reference layout: the owner's Google Sheet (see `../product/REQUIREMENTS.md`). One block per tier
  (Grey ×64, Green ×16, Blue ×4, Legendary ×1) with columns Material, Qty, Cost per, Total Cost, then
  Craft chance and Needed, and a grand total with tax at the bottom.
- Numbers (Kinah amounts) are the content: tabular figures, thousands separators.
- Every price must show where it came from (OCR, manual override, or missing) and how old it is.

## Principles
1. **The numbers are the interface.** Chrome stays quiet (greys); colour is spent on meaning: gold =
   interactive/selected, tier colours = grade identity, status colours = state.
2. **Inset = editable.** Anything the user can type into (inputs, editable cells) sits on the darker
   inset surface with a visible border. Computed values never do.
3. **Glanceable from across a desk.** Totals and the capture status must read at a glance while the
   game has focus on the other monitor.
4. **Never colour alone.** Tiers carry their name; states carry a word or sign.

## Colour tokens (dark only)
Contrast ratios are WCAG 2.x, computed against the surface they're used on.

### Surfaces and borders
| Token | Hex | Use |
|---|---|---|
| `bg.app` | `#000000` | Main window background, gutters between tier blocks |
| `bg.surface` | `#1A1A1A` | Tier blocks, panels, dialogs, tab bar, status bar |
| `bg.raised` | `#242424` | Table headers, hover, menus, popups, tooltips, toasts |
| `bg.inset` | `#0D0D0D` | Inputs, editable cells, search field |
| `bg.selected` | `#2B2616` | Selected row / list item (gold-tinted) |
| `border.subtle` | `#333333` | Dividers, block outlines, grid lines (decorative) |
| `border.control` | `#707070` | Input, checkbox, secondary-button borders: 3.5:1 on surface, 3.1:1 on raised, 3.9:1 on inset (meets 3:1 non-text) |

### Text
| Token | Hex | on `surface` | on `raised` | on `inset` | on `selected` |
|---|---|---|---|---|---|
| `text.primary` | `#E8E6E1` | 13.9:1 | 12.4:1 | 15.6:1 | 12.1:1 |
| `text.secondary` | `#B3B3B3` | 8.3:1 | 7.4:1 | 9.3:1 | 7.2:1 |
| `text.muted` | `#8F8F8F` | 5.4:1 | 4.8:1 | 6.0:1 | 4.7:1 |
| `text.disabled` | `#666666` | 3.0:1 (exempt, disabled only) | | | |

`text.muted` is never used on `#333333` (3.9:1).

### Accent (gold)
| Token | Hex | Use / contrast |
|---|---|---|
| `accent` | `#C9A84C` | Primary button fill, focus ring, selected-tab underline, links, manual badge. As text: 7.6:1 on surface, 6.8:1 on raised, 6.6:1 on selected |
| `accent.hover` | `#D4B65E` | Primary button hover |
| `accent.pressed` | `#A88A3A` | Primary button pressed |
| `on.accent` | `#0D0D0D` | Text on gold: 8.5:1 on `accent`, 9.9:1 on hover, 5.9:1 on pressed |

Bright `#FFD700` is **not used**. The source caps saturation; one gold keeps the accent meaningful.

### Tier grades
Global's item grades, lowest first: Common (grey), Rare (green), Epic (blue), Unique (gold in game).
There's no Heroic on Global (owner, 2026-10-05). A tier takes the colour of its normal result's grade
(Ruby Necklace Common → Expert's Rare → Artisan's Epic → Star Dragon Lord Unique).
Used only for the tier marker, tier name label and recipe-picker grade label, never as fills.
**Unique is orange here, although the game shows it gold,** so it can't be mistaken for the
interactive gold accent (rule approved with this draft).
| Token | Hex | on `surface` | on `raised` |
|---|---|---|---|
| `tier.common` | `#9E9E9E` | 6.5:1 | 5.8:1 |
| `tier.rare` | `#5DBB63` | 7.3:1 | 6.5:1 |
| `tier.epic` | `#5B9BE6` | 6.0:1 | 5.4:1 |
| `tier.unique` | `#E07B39` | 5.9:1 | 5.2:1 |

### Status
| Token | Hex | on `surface` | on `raised` | Use |
|---|---|---|---|---|
| `status.positive` | `#4FC3A1` | 8.0:1 | 7.1:1 | Profit, capture succeeded. Teal-leaning so it doesn't read as tier green |
| `status.warning` | `#F0D875` | 12.3:1 | 10.9:1 | Missing price, stale price, shortfall, low-confidence OCR match |
| `status.danger` | `#EF6B6B` | 5.8:1 | 5.2:1 | Loss, capture failed, invalid input |

Status colour always comes with a word, sign (`+` / `−`) or `!` prefix.

## Typography
Fonts: **Inter** (UI text) and **JetBrains Mono** (every number: Kinah, Qty, %, successes, crafts,
ages, chart axes). Both SIL Open Font License 1.1. JetBrains Mono digits are fixed-width, so columns
align without OpenType features; don't set numbers in Inter (if unavoidable, enable `tnum`).

Sizes in **px** in QSS (Qt scales px with Windows display scaling; avoid pt so QSS and QFont agree).
| Role | Font | Size / weight | Use |
|---|---|---|---|
| `display.num` | Mono | 20px / 600 | Total cost, Profit |
| `heading` | Inter | 18px / 600 | Recipe name |
| `title` | Inter | 14px / 600 | Panel titles, tier name in header |
| `body` | Inter | 13px / 400 | Default UI text, material names |
| `body.num` | Mono | 13px / 400 | Table numbers, inputs with numbers |
| `label` | Inter | 12px / 600 | Column headers, field labels, tab labels (sentence case) |
| `caption` | Inter | 12px / 400 | Helper text, status bar, toast body |
| `badge` | Inter | 11px / 600, uppercase, letter-spacing 0.5px | Provenance and state badges |
| `caption.num` | Mono | 11px / 400 | Price age (`2h`, `3d`) |

Minimum size 11px, badges and ages only. Line height ≈ 1.4 (Qt default is fine).

### Number formatting
- Kinah: integer, comma thousands separators (`1,234,567`), right-aligned. Unit in the column header
  ("Cost per (Kinah)"), not in every cell.
- Successes and crafts: one decimal (`68.7`, `4.0`). Percentages: one decimal (`93.1%`); inputs accept
  two. Round for display only (see `CLAUDE.md`).
- Negatives use U+2212 `−`, never parentheses. Missing values show `—` in `text.muted`.

## Spacing, size, shape
- Base unit 8px; half-step 4px allowed inside controls. Tokens: 4, 8, 12, 16, 24, 32.
- Window: minimum 960×640, default 1280×800. Content margin 16px; gap between tier blocks 16px.
- Control height 32px (buttons, inputs, combos). Table rows 28px; table header 28px. Tab bar 40px.
  Status bar 28px.
- Radii: 4px controls/badges, 6px blocks/panels/toasts. Nothing rounder.
- No shadows except menus/popups/toasts (Qt draws none by default; leave it).

## Motion
None in the MVP. Hover/press are instant state changes. The only allowed transition is a 150ms
opacity fade on toasts, and only if trivial to do; otherwise none.

## Layout

### Main window
```
┌ Header (surface, 56px): [Recipe search ⌕ Ctrl+K ........] [Calculator | Prices | Settings] ┐
├ Calculator: tier blocks (scroll, bg.app)                    │ Summary panel 280px (surface) ┤
├ Status bar (surface, 28px): capture status · hotkey · last capture time                     ┘
```
- Tabs (`QTabBar`, top): Calculator, Prices (price list + history), Settings. Sidebar rejected: three
  destinations don't justify the width on a half-screen window.
- Summary panel is fixed at the right at all widths (min window width 960 still leaves ~620px for
  the table).

### Tier block (Calculator)
One block per tier, in chain order Common → Rare → Epic → Unique. `bg.surface`, radius 6px, 1px
`border.subtle`, 4px left border in the tier colour, padding 12px 16px.

Header row (one line, wraps to two below ~1100px):
- Left: the recipe's name in `title` coloured with its grade token (e.g. `Expert's Ruby Necklace`
  in `tier.rare`) plus `Tier 2 of 4 · Rare` in `caption` `text.secondary`. The words are the
  non-colour identity.
- Inputs: `Chance [ 93.1 %]`, `Combo [ 25.0 %]`, inset 72px-wide fields, `label` before each.
- Computed: `Successes 16.0` · `Crafts 17.2` (Mono, `text.primary`, labels `text.secondary`).
- Right: `Tier cost 1,234,567` (Mono 13px/600, primary) and `Lost 925,925` (Mono, `text.secondary`;
  it's an expected cost, not an error, so not red).
- Later (buy vs. craft): a two-option segmented control `Craft | Buy` with the cheaper option marked
  `CHEAPER` badge (positive outline). TODO (owner): auto-pick cheaper or let the user choose?

Material table columns:
| Col | Width | Align | Content |
|---|---|---|---|
| Incl. | 32px | centre | Checkbox; unchecked = excluded from cost |
| Material | stretch, min 180px | left | Name, `body` |
| Qty | 56px | right | Mono |
| Cost per | 112px | right | Mono; editable (inset cell) for manual override |
| Source | 104px | left | Provenance badge + age |
| Total | 120px | right | Mono |

- Excluded row: name and numbers in `text.muted` with strikethrough on Total; Incl. unchecked;
  tooltip "Excluded from cost". Tier cost ignores it.
- Header row: `bg.raised`, `label` `text.secondary`. No zebra striping; 1px `border.subtle` row
  dividers.

### Summary panel
Stacked label/value rows, label `body` `text.secondary` left, value Mono right, 8px row gap:
Craft total → Buy tax (10%) `+` → **Total cost** (`display.num`) → divider → Sell price (inset input) →
Sell tax (10%) `−` → Net sale → **Profit** (`display.num`, `status.positive` with `+` and word
"Profit", or `status.danger` with `−` and "Loss"). Before a sell price exists: Profit shows `—` and
"Enter a sell price". Warnings for the recipe (e.g. "2 materials have no price") list under Total cost
in `status.warning` `caption` with `!`.

### Prices tab
Left: searchable item list 280px (name, latest price Mono, age). Right: line chart above an
observations table (Time, Unit price, Qty, Source).
- Chart: 2px `accent` line, straight segments (no smoothing, no area fill, no gradient). OCR points
  6px filled gold; manual points 7px hollow gold ring. Horizontal grid lines only, 1px
  `border.subtle`. Axis labels `caption.num` `text.secondary`. Hover tooltip: price, time, source.
- Range: segmented `24h | 7d | 30d | All`, default 7d.
- Empty: "No prices for this item yet. Search it in the auction house and press <hotkey>."

### Recipe picker
Search field in the header (inset, 320px, placeholder "Search recipes (Ctrl+K)"). Popup list below
it, `bg.raised`, max 10 visible rows of 32px: name `body` with matched text 600, grade label in tier
colour `caption` 600, category `caption` `text.secondary` right-aligned. Up/Down/Enter/Esc. Empty
query shows recently opened recipes (TODO owner: wanted?). No results: "No recipe matches “xyz”".

### Settings
Single column form, max 480px wide, label left (160px, `body` `text.secondary`), control right.
Groups: Taxes (Buy %, Sell %), Capture (hotkey recorder field, "Test capture" secondary button),
Prices (stale after N hours). Changes apply immediately; no Save button.

## Components
**Buttons** (32px, padding 0 16px, radius 4, `label` weight):
- Primary: `accent` fill, `on.accent` text; hover `accent.hover`; pressed `accent.pressed`. One per
  view at most.
- Secondary: transparent, 1px `border.control`, `text.primary`; hover `bg.raised`.
- Ghost: no border, `accent` text; hover `bg.raised`.
- Disabled: `text.disabled`, border `border.subtle`, no fill.

**Inputs / editable cells:** `bg.inset`, 1px `border.control`, radius 4, padding 0 8px, Mono for
numbers (right-aligned) and Inter for text. Focus: 2px `accent` border (reduce padding by 1px so
text doesn't shift). Invalid: 2px `status.danger` border + `caption` message below (or tooltip in a
cell). In tables, an editable cell shows the inset background permanently so it's findable without
hovering; edit mode adds the gold border.

**Checkbox:** 16px box, Fusion indicator driven by QPalette (Base `bg.inset`, Highlight `accent`,
check mark `on.accent`). Avoid QSS `::indicator` styling unless the main session adds a check-mark
image asset.

**Badges** (18px tall, padding 0 6px, radius 4, `badge` type, 1px border, transparent fill):
- `OCR`: `text.secondary` text, `border.control` border.
- `MANUAL`: `accent` text and border. Tooltip shows the OCR value it overrides, if any.
- `! MISSING`: `status.warning` text and border. Value cell shows `—`, cost counts as 0.
- Age after the badge, `caption.num` `text.muted` (`12m`, `5h`, `3d`); stale (older than the
  Settings threshold) turns `status.warning` with a `!` prefix. Tooltip: full timestamp.
- `REVIEW` (low-confidence OCR match): `status.warning`.

**Tabs:** text `label` `text.secondary`; hover `text.primary`; selected `text.primary` + 2px `accent`
bottom border. Padding 0 16px.

**Status bar** (capture feedback, always visible): left `Capture: <hotkey>` in `text.secondary`;
centre the last result: idle `text.muted` "Ready"; working `text.primary` "Reading listings…";
success `status.positive` "Captured 7 listings · <item> · 12s ago"; failure `status.danger`
"Capture failed: auction house list not found". Review needed: `status.warning` "3 rows need
review" as a clickable ghost link.

**Toasts** (in-window, bottom-right, 16px from edges): 320px wide, `bg.raised`, 1px
`border.subtle`, 4px left border in the status colour, radius 6, padding 12px 16px; title `body` 600,
detail `caption` `text.secondary`. Success auto-dismisses after 4s; failures stay until closed
(ghost `Close` button, Esc). Max 3 stacked, 8px gap. Same text as the status bar so nothing is lost
if missed.

TODO (owner): when the game has focus and the app is hidden, should a capture also give a Windows
notification or a short sound? (Main session decides the mechanism.)

**Tooltips:** `bg.raised`, 1px `border.subtle`, `caption` `text.primary`, padding 4px 8px.

**Scrollbars:** 10px, transparent track, handle `#4D4D4D` radius 5, hover `border.control`.

## Keyboard and focus
- Every action works by keyboard. Tab order follows reading order: header search → tabs → tier
  blocks top to bottom (chance, combo, then table) → summary inputs.
- Ctrl+K / Ctrl+F: recipe search. Ctrl+1/2/3: tabs. In tables: arrows move, Enter or F2 edits, Esc
  cancels, Space toggles Incl., Delete on Cost per clears the manual override (back to OCR).
- Focus is always visible: 2px `accent` border on inputs/cells/buttons; on the primary (gold) button
  use a 2px `text.primary` border instead. Never remove focus rects without a replacement.
- Global capture hotkey default: TODO (owner); must not clash with common game keys.

## Qt implementation notes
- Use the **Fusion** style plus a dark **QPalette** for the base (so dialogs, menus, checkboxes and
  native-drawn parts are dark), then one app-wide **QSS** sheet for the specifics above. QPalette:
  Window `#1A1A1A`, WindowText/Text/ButtonText `#E8E6E1`, Base `#0D0D0D`, AlternateBase `#1A1A1A`,
  Button `#242424`, Highlight `#C9A84C`, HighlightedText `#0D0D0D`, PlaceholderText `#8F8F8F`,
  ToolTipBase `#242424`, ToolTipText `#E8E6E1`, Link `#C9A84C`, Mid/Dark `#333333`; Disabled
  Text/WindowText/ButtonText `#666666`.
- Table selection: set `selection-background-color: #2B2616; selection-color: #E8E6E1` in QSS
  (palette Highlight is gold for checkboxes, too heavy for rows).
- Keep tokens in one Python module (single source for QSS, palette and chart colours); generate the
  QSS from it rather than hard-coding hex in widgets.
- Fonts: bundle static TTFs (Inter Regular/Medium/SemiBold; JetBrains Mono Regular/SemiBold) and
  register with `QFontDatabase.addApplicationFont` at startup; static instances avoid variable-font
  weight issues on Windows. Fallbacks: Segoe UI, Consolas. **Licence:** both OFL 1.1; ship each
  `OFL.txt` with the fonts in the packaged build and credit them in README/About. Flag for main
  session: font files and packaging are an architecture decision (record in `ARCHITECTURE.md`).
- Dark title bar: Qt follows the Windows colour scheme, so a light-mode Windows user gets a white
  title bar. Flag for main session: force dark (e.g. Qt 6.8+ `QStyleHints.setColorScheme`) or accept.
- Chart: QtCharts (PySide6 Addons) vs. a small QPainter widget is a dependency decision for the main
  session; the spec above works with either.
- Display scaling: test at 100%, 125% and 150%; px values above are logical pixels.

## Avoid
- Gradients (gold or otherwise), glassmorphism, blur, glow, drop shadows on blocks.
- `#FFD700` and any second accent; gold used for decoration instead of interaction/selection.
- Pure white `#FFFFFF` text or any light surface.
- Tier colours as row or block fills; tier identity by colour alone.
- Red for "Lost" (it's the expected cost of combo crafting, not an error).
- Emoji or pictographic icons; icon-only buttons without a text label or tooltip.
- Zebra striping, card grids, dashboards of KPI tiles, decorative charts.
- Animation (spinners excepted only if a wait exceeds ~1s; prefer status bar text).
- Abbreviating Kinah (`1.2M`) in tables; full numbers only. (Chart axes may abbreviate.)
- Proportional digits anywhere numbers line up.

## Open (owner)
- Stale-price threshold default (suggest 24h).
- Default capture hotkey.
- Capture feedback when the app is hidden (notification/sound).
- Recently opened recipes in the picker.
- Buy vs. craft: auto-pick cheaper or user choice.
