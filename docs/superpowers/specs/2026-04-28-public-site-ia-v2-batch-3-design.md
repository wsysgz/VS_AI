# Public Site IA V2 Batch 3 Design

**Date:** 2026-04-28
**Workspace:** `D:\GitHub\auto`
**Depends on:** `D:\GitHub\auto\docs\superpowers\plans\2026-04-28-public-site-ia-v2.md`, `D:\GitHub\auto\docs\superpowers\plans\2026-04-28-public-site-ia-v2-batch-2.md`

## Goal

Define the third IA V2 batch for the public Pages site so the new `赛道` and `来源` surfaces become easier to search and remain comfortable to use on narrow mobile screens.

This batch should finish two user-visible problems together:

1. list pages need direct in-page filtering instead of forcing manual scanning,
2. navigation and card layouts need a tighter mobile presentation now that more entry points exist.

## Scope

This batch is a static-site usability pass on top of the existing IA V2 first and second batches.

In scope:

- add in-page search/filter inputs to `/tracks/` and `/sources/`
- keep filtering fully static and client-side
- tighten mobile navigation wrapping and chip density
- reduce small-screen card layout pressure on homepage, tracks, and sources surfaces
- update handoff and roadmap docs so repo truth matches the current IA V2 status

Out of scope:

- adding a new page type
- adding server-side or runtime search infrastructure
- introducing a frontend framework
- redesigning the visual language of the public site
- changing report payload schema or archive data contracts
- doing a remote release confirmation in this same step unless the user asks for it later

## Current State

The public site already has these IA surfaces locally completed:

- homepage `日报` entry and daily index
- `/tracks/` index and per-track pages
- `/sources/` index and per-source pages
- archive source filter search
- cross-page navigation for `赛道` and `来源`

The remaining usability gap is uneven:

- archives already support source search,
- tracks and sources still require manual scanning,
- mobile width now has more top-level links and chips competing for the same horizontal space.

This means batch 3 should finish the interaction model rather than add another information surface.

## User Decisions Already Made

- implement `赛道/来源` list-page search first
- implement mobile navigation and card compression in the same push
- keep the current static generator model
- do not split this into a new frontend or a separate runtime
- keep the work on `main`

## Product Direction

### 1. Search Model

The chosen search model is a minimal static filter, not a separate search system.

Each list page should expose one input at the top of the list section:

- `/tracks/`: `筛选赛道`
- `/sources/`: `筛选来源`

The filter should work instantly in the browser by hiding non-matching cards.

This keeps behavior consistent with the existing archive source filter and avoids inventing a second interaction style.

### 2. Matching Rules

#### Tracks page

Track filtering should match against visible track-card content:

- track name
- latest title/judgment text shown on the card

#### Sources page

Source filtering should match against visible source-card content:

- source name
- latest title text
- top-track labels rendered on the card

No advanced query syntax is needed. Plain substring matching is enough for this batch.

### 3. Mobile Reading Model

The mobile direction should stay dense but readable, not card-heavy and not collapsed into hidden menus.

The top bar should remain fully visible and static, but it needs more disciplined wrapping:

- smaller gaps between nav items
- links grouped by natural wrapping rather than stretched alignment
- no overlapping text

The homepage chip row should also remain visible, but use tighter spacing and allow clean multi-line flow.

## Interaction Design

### 1. Tracks Index

The `赛道` page should keep the current intro section, then add a search shell before the card grid.

Recommended structure:

1. section title and subtitle
2. filter input
3. archive-style grid of track cards

When the user types:

- cards that match stay visible
- cards that do not match are hidden
- no page reload occurs

### 2. Sources Index

The `来源` page should mirror the same interaction pattern as tracks:

1. section title and subtitle
2. filter input
3. source card grid

This symmetry matters because `赛道` and `来源` are now peer entry points in IA V2.

### 3. Mobile Card Compression

The cards should not change hierarchy, but they do need more predictable small-screen behavior:

- action buttons should remain on their own line when needed
- long source titles should not squeeze buttons vertically
- metadata and tag rows should wrap cleanly
- grids should degrade to one column early enough to avoid cramped two-column cards on phones

## Technical Design

### 1. Implementation Boundary

Keep all site-generation changes inside:

- `src/auto_report/outputs/pages_builder.py`

Do not add new modules for this batch unless a helper becomes clearly reusable inside the same file.

### 2. Filtering Implementation

Reuse the archive pattern:

- render each card with searchable `data-*` text
- attach a small inline script per page
- toggle `style.display` based on substring match

This is sufficient because track and source indexes are static lists and already fit the current page-builder approach.

### 3. CSS Changes

All visual tightening should remain in `_base_css()` and should focus on:

- `nav-links`
- chip spacing
- mobile breakpoints
- grid minimum widths
- footer/action alignment for cards

No new stylesheet files are needed.

## Documentation Design

The docs must stop describing IA V2 batch 2 as only an evaluation item.

Required doc updates:

- `V1升级方案.md`
- `交接备忘录.md`
- `AI对接手册.md`

These updates should state:

- IA V2 batch 2 is locally completed
- current next step is IA V2 batch 3
- batch 3 scope is track/source filtering plus mobile layout tightening

## Testing Design

Add focused regression coverage in `tests/test_pages_builder.py`.

Required checks:

1. `/tracks/` contains a track filter input and filtering script hook
2. `/sources/` contains a source filter input and filtering script hook
3. generated markup includes the searchable card metadata needed by the scripts
4. mobile-oriented CSS rules exist for the tightened navigation / chip / grid behavior

The tests should remain structural. They do not need browser automation for this batch.

## Verification

Local acceptance for this batch should include:

1. `python -m pytest tests/test_pages_builder.py -q`
2. `python -m pytest tests -q`
3. `python -m auto_report.cli build-pages`
4. visual check in the local preview at `http://127.0.0.1:8765/`

Visual review should confirm:

- `赛道` page can be filtered directly
- `来源` page can be filtered directly
- mobile-width nav/chip wrapping is cleaner than before
- cards stay readable and actions remain tappable

## Rollout Recommendation

Implement batch 3 as one locally verified pass:

1. tests for track/source filtering and mobile CSS hooks
2. minimal page-builder implementation
3. generated Pages rebuild
4. roadmap and handoff doc refresh

Do not split search and mobile tightening into separate pushes. They solve one usability problem and should ship together.
