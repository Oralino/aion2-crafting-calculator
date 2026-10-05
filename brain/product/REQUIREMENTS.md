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

## Calculation rules
Confirmed from the owner's sheet and in-game screenshots of the Ruby Necklace chain (2026-10-05).
- A craft is a **combo chain** of recipes, one per tier, named by the grade of their normal result:
  Common → Rare → Epic → Unique (e.g. Ruby Necklace → Expert's → Artisan's → Star Dragon Lord
  Necklace). Each tier has its own materials (Qty per craft × Cost per unit), and different
  accessories use different materials. (The sheet called the tiers Grey/Green/Blue/Legendary.)
- **Combo:** a successful craft has a combo chance (25% by default, editable per tier) to produce the
  "Splendent" version instead of the normal item. **Each craft of the next tier uses up one
  Splendent item from the tier below, and a failed craft uses it up too** (the chain has to restart).
  Only combo results count; normal results have no value.
- **Needed crafts**, from the final target (default 1) down: attempts on a tier = successes ÷ craft
  chance (the in-game proficiency success rate); the tier below must make that many combo items, so
  its successes = those attempts ÷ combo rate. With no failures this gives the sheet's 64/16/4/1;
  failures raise every lower tier (the sheet's Accessories: about 73.8/17.5/4.2/1 successes).
- Tier cost = attempts × sum of that tier's included material costs.
- **Lost value:** failures and non-combo results (about 75% of successes) have no value, but their
  materials are spent. Their share of each tier's cost is shown as "lost", and all of it counts in
  the cost of the final item and its profit.
- **Per-material exclusion:** every material in the recipe counts by default; the user can exclude
  one (e.g. already owned) with Incl. (The sheet's top-tier formula skipped two materials; the app
  follows aion2hub's recipe instead, owner 2026-10-05.)
- Total = sum of all tiers, then tax (see Owner decisions).
- Some materials have no market price (shown as `-` in the sheet), e.g. Diamond Decoration, Odyle.
  They're treated as 0 cost unless a price is entered.

## MVP features
1. **Recipes for all craftable items**, imported from aion2hub (see Owner decisions). Each tier and
   material shown like the sheet's blocks.
2. **Hotkey OCR capture:** the user searches an item in the auction house, presses a hotkey, and the
   app reads the visible listings (item name, unit price, quantity) and stores them.
3. **Price rule:** "Cost per" = the **lowest current listing** unit price. Every price can be
   overridden by hand.
4. **Craft chance:** entered per tier from the in-game crafting panel (the recipe source has no
   success rates); the combo rate defaults to 25% and can be changed per tier.
5. **Buy vs. craft per tier:** for each intermediate Splendent item (e.g. Expert's Splendent Ruby
   Necklace), compare buying it on the market with crafting it, and use the cheaper path.
6. **Profit:** compare total crafting cost with the finished item's market price. The top tier's
   successes also combo (25% by default) into the Splendent version, so the sale is an expected
   value: (1 − combo) × sell price + combo × Splendent sell price, then sell tax. Without a
   Splendent price it's valued at the normal price, with a warning (owner, 2026-10-05).
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
- **Recipes follow aion2hub**: all listed materials count by default; the owner reports any recipe
  that looks wrong in game (2026-10-05). This replaces the sheet's top-tier exclusions.
- **Failed crafts use up the lower tier's Splendent item** (2026-10-05).
- **Global grades** are Common, Rare, Epic and Unique (gold); there is no Heroic on Global
  (2026-10-05).
- **Combo rate is 25% for every weapon and accessory recipe** (2026-10-05); it stays editable.
- Top-tier "Splendent" items (e.g. Splendent Dark Dragon Lord Boots) are the 25% combo result of
  their normal recipe, even where aion2hub lists a separate recipe for them (2026-10-05).
- **Recipe source: aion2hub.com HTML pages**, scraped at dev time, throttled, for personal use
  (2026-10-05). Its `/api/` is disallowed by robots.txt and is not used.
- **Craft chance** is the in-game proficiency success rate (shown in the crafting panel). A
  proficiency-based chance curve is a later feature.
- Weapon crafting is left out of the sheet reference; weapon recipes come from the owner's list or the
  recipe source.

## Acceptance criteria (MVP)
- Given the sheet's Accessories (Diamond Earrings) prices, chances and tax, the cost follows the rules
  above (the sheet's own totals are lower: it treated failures as free and skipped two top-tier
  materials).
- A hotkey capture of an auction house search reads names, unit prices and quantities correctly on the
  test screenshots at every supported resolution.
- Captured prices appear in the calculator and in price history without manual entry.
- Runs from the packaged `.exe` on a Windows PC without Python installed.

## Out of scope
Non-English clients, macOS/Linux, a web version, accounts or a backend, real-money trading.

## Open decisions
- **Shortfall rule:** when the cheapest listing has fewer units than needed (need 22, cheapest has 5).
  Default until decided: lowest unit price, with a warning.
- **Supported resolutions list:** TBD (needs owner screenshots).
