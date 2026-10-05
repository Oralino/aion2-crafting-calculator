# DESIGN.md
Visual source of truth, maintained by design-advisor. **Status: not drafted yet.** design-advisor
drafts it before the first UI screen is built; the owner approves.

## Known constraints
- PySide6 desktop app on Windows; used alongside the game (often on a second monitor or alt-tabbed).
- Reference layout: the owner's Google Sheet (see `../product/REQUIREMENTS.md`). One block per tier
  (Grey ×64, Green ×16, Blue ×4, Legendary ×1) with columns Material, Qty, Cost per, Total Cost, then
  Craft chance and Needed, and a grand total with tax at the bottom.
- Numbers (Kinah amounts) are the content: tabular figures, thousands separators.
- Every price must show where it came from (OCR, manual override, or missing) and how old it is.
