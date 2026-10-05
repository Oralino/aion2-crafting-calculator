# REQUIREMENTS.md
What the app must do, and the owner's decisions behind it. How it works is in
`../engineering/ARCHITECTURE.md`.

## Goal
**Aion2 Crafting Calculator** is a Windows desktop app that tells an Aion 2 (Global, English client)
player what a craft really costs and whether it's worth doing. Prices are read from the in-game
auction house (the cross-server World Brokerage) with OCR. Users: the owner and friends/guild members
it's shared with as a packaged `.exe`.

Starting point: the owner's Google Sheet
(<https://docs.google.com/spreadsheets/d/1G_dSqPojs0LzykVN5gjSZu5Af8wJaLuvagsPUaw2QqQ>), tabs
"Accessories" (the reference) and "Weapon WIP" (ignored: weapon recipes will come from the owner's
list or the recipe source). The app replaces it; its calculation rules are below.

## Calculation rules (from the sheet)
- A craft is a **tier chain**: Grey ×64 → Green ×16 → Blue ×4 → Legendary ×1. Each tier has its own
  materials (Qty per craft × Cost per unit).
- **Needed crafts** for a tier = target count ÷ craft chance (e.g. `64 / 0.931`). Tier cost = needed ×
  sum of that tier's included material costs.
- **Per-material exclusion:** a material can be excluded from the cost sum. The sheet does this on
  purpose for the Legendary tier (Artisan's Ultimate Refining stone and Enhanced Thick Balaur are left
  out). Reason: TBD (owner).
- Total = sum of all tiers, then tax (see Owner decisions).
- Some materials have no market price (shown as `-` in the sheet), e.g. Diamond Decoration, Odyle.
  They're treated as 0 cost unless a price is entered.

## MVP features
1. **Recipes for all craftable items**, imported from a community database (source TBD, see Open
   decisions). Each tier and material shown like the sheet's blocks.
2. **Hotkey OCR capture:** the user searches an item in the auction house, presses a hotkey, and the
   app reads the visible listings (item name, unit price, quantity) and stores them.
3. **Price rule:** "Cost per" = the **lowest current listing** unit price. Every price can be
   overridden by hand.
4. **Craft chance:** the recipe data's rate is the default; the user can override it per tier.
5. **Buy vs. craft per tier:** for each intermediate (e.g. Blue), compare buying it on the market with
   crafting it, and use the cheaper path.
6. **Profit:** compare total crafting cost with the finished item's market price.
7. **Tax, configurable:** separate buy-side tax (applied to material cost, the sheet's ×1.1) and
   sell-side tax (deducted from the sale price in the profit calc). Default 10% each: TBD (owner)
   to confirm defaults.
8. **Price history:** every OCR reading is stored with a timestamp; show a price trend per item.
9. **Multiple resolutions:** OCR must work across common screen sizes, not one fixed layout.

## Later (not MVP)
- **Automated scan** (the app types searches and pages through the auction house for a list of items).
  Opt-in only, with a clear warning: automating game input may break NCSoft's terms of service and be
  flagged by anti-cheat, risking the user's account.

## Owner decisions (2026-10-05)
- Desktop app, shared with others as a Windows `.exe`.
- OCR is the price source: no official or public Aion 2 market API was found. Community sites
  (aion2hub.com, gamers4.life) extract item data from the game client but don't publish live prices.
- Hotkey capture first; automated scan later as an opt-in (ban risk accepted only as opt-in).
- Recipes scraped from a community database rather than entered by hand.
- English client; multiple resolutions.
- The Legendary-tier exclusions in the sheet are intentional.
- Weapon crafting is left out of the sheet reference; weapon recipes come from the owner's list or the
  recipe source.

## Acceptance criteria (MVP)
- Reproduces the sheet's Accessories totals given the same prices, chances, exclusions and tax.
- A hotkey capture of an auction house search reads names, unit prices and quantities correctly on the
  test screenshots at every supported resolution.
- Captured prices appear in the calculator and in price history without manual entry.
- Runs from the packaged `.exe` on a Windows PC without Python installed.

## Out of scope
Non-English clients, macOS/Linux, a web version, accounts or a backend, real-money trading.

## Open decisions
- **Recipe data source:** which community database, how complete its recipes and craft chances are,
  and whether its terms allow scraping. Fallback: hand-entered JSON.
- **Tier relationship:** whether lower-tier items are consumed by the next tier (an upgrade chain) or
  are separate crafts. Decides how "buy vs. craft per tier" works.
- **Shortfall rule:** when the cheapest listing has fewer units than needed (need 22, cheapest has 5).
  Default until decided: lowest unit price, with a warning.
- **Why the Legendary exclusions:** already owned, bought elsewhere, or something else. TBD (owner).
- **Supported resolutions list:** TBD (needs owner screenshots).
