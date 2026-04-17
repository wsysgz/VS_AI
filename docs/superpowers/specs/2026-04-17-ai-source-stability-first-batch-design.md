# AI Source Stability First Batch Design

## Goal

Stabilize the first batch of high-priority `AI/LLM/Agent` sources by replacing generic fragile listing extraction with source-specific structured extraction on official update pages, then align governance metadata so those upgraded sources no longer look like pending replacement candidates.

## Scope

This batch only touches sources that already use official first-party pages and have a stable, repeatable page structure in the current environment:

- `deepseek-updates`
- `moonshot-blog`

`qwen-blog`, `anthropic-news`, and the `AI x Electronics` sources stay out of this first implementation batch because the available entry points either do not expose a stable machine-readable structure from the current collector or still need separate validation.

## Approach Options

### Option 1: Keep generic listing extraction and only tweak selectors

Pros: smallest diff.
Cons: still depends on brittle link-card structure and keeps governance marking these sources as fragile replacement candidates.

### Option 2: Add a structured website-page mode for official update timelines

Pros: keeps official first-party pages, uses explicit container/title/link selectors, and lets governance classify the upgraded pages as stable enough to keep polling directly.
Cons: requires a small collector/parser extension and a few tests.

### Option 3: Force RSS/RSSHub replacement now

Pros: strongest long-term machine-readability when a real feed exists.
Cons: not justified for this batch because the targeted sources do not currently expose a verified official feed URL from the available evidence.

## Recommendation

Use Option 2.

This gives the first batch a real production effect without inventing unverified feed replacements. It is also compatible with the user preference to prioritize first-hand AI sources and to do the direct source hardening before broader governance work.

## Design

### Source model

Add a dedicated website source mode for structured official update pages. The mode will still fetch the official page with requests, but instead of treating every matching anchor as a card, it will parse a configured entry container and then resolve title, link, and optional date fields from that container.

### Collector behavior

The website collector will dispatch based on `mode`:

- existing `article_listing` behavior remains unchanged
- new structured mode uses source-defined selectors to extract entries from timeline-style pages

This keeps the diff surgical and avoids changing unrelated collectors.

### Governance behavior

Structured official update pages should not continue to look like fragile replacement candidates by default. For the new structured mode:

- stability tier should default to a direct-page stable classification
- watch strategy should reflect direct polling of the official page
- replacement target should default to `none`
- candidate kind should default to `none`

That turns the first batch into a real `A` change, then naturally performs the matching `B` cleanup for those same sources.

### Initial migrated sources

- `deepseek-updates`: convert to the new structured mode using the current official changelog page
- `moonshot-blog`: convert to the new structured mode using the current official Moonshot blog overview page

### Testing

Add tests for:

- structured page extraction returning the right titles and URLs
- website collector dispatching to the new extractor
- source registry assigning stable governance defaults to structured official pages
- settings loading the migrated source modes cleanly
