# P1 Governance Closure Design

> Workspace: `D:\GitHub\auto`
>
> Scope: close the remaining P1 operational governance tail items without expanding into full P2 implementation.

## Goal

Turn the current source governance output from a passive classification artifact into an operationally useful P1 closure loop:

1. generate a first real `changedetection` watch list
2. expose a priority-ranked governance queue for on-call / maintenance work
3. surface both outputs in existing artifacts and the ops dashboard
4. define, but do not yet implement, the P2 gateway/tracing and P2.5 OpenCLI pilot handoff

## Why this is the right boundary

The repo already has:

- source classification
- candidate grouping
- source governance JSON output
- ops dashboard tables

What is still missing is the last-mile operational shape:

- which sources should become `changedetection` watches first
- which governance items deserve attention first
- what exact queue a maintainer should act on next

This is still P1 work. It improves source stability directly and does not require introducing new runtime dependencies or infrastructure.

## Current repo reality

The current logic in `D:\GitHub\auto\src\auto_report\source_registry.py` already computes:

- `manual_review`
- `rsshub_candidates`
- `changedetection_candidates`
- `replacement_candidates`

But the current output still has three gaps:

1. the `changedetection_candidates` list is only a bucket, not a watch-ready checklist
2. the governance output is grouped, but not prioritized for operations
3. the ops dashboard exposes raw sections, but not one clear “what to do next” queue

## Design summary

This batch adds three concrete layers and one documentation handoff layer.

### Layer 1: Watch-ready changedetection queue

Add a new derived list inside source governance output for sources that should become `changedetection` watches.

Each row should include:

- `source_id`
- `collector`
- `enabled`
- `category_hint`
- `stability_tier`
- `watch_strategy`
- `url`
- `watch_target`
- `reason`
- `priority`
- `next_action`

Design rule:

- `watch_target` is usually the current source `url`
- `reason` explains why this belongs in `changedetection`
- `priority` is a small integer or label derived from transparent rules

This is still an artifact-level checklist. It does not create external watches automatically.

### Layer 2: Governance priority queue

Add a single merged, sorted queue that answers:

> If a maintainer has 20 minutes, which governance items should be touched first?

Each queue row should include:

- `source_id`
- `category_hint`
- `candidate_kind`
- `stability_tier`
- `enabled`
- `priority_score`
- `priority_label`
- `reason`
- `next_action`
- `url`

Priority rules should be simple and inspectable, for example:

- `manual_replace` > `changedetection_watch` > `rsshub_route`
- `ai-llm-agent` and `ai-x-electronics` get a small boost over generic buckets
- enabled fragile sources rank above disabled placeholders
- already stabilized `rss` / `json_api` / `structured_page` sources do not enter the queue

The main principle is not “perfect ranking”. It is “stable enough that different maintainers will make the same next-step choice.”

### Layer 3: Ops dashboard operational view

Keep the current governance sections, but add one prominent queue view:

- `Governance Priority Queue`

This section should display the merged ranked queue first, followed by the raw grouped sections already present today.

That preserves current visibility while making the dashboard operationally useful.

### Layer 4: P2 / P2.5 handoff notes

This batch does not implement:

- LiteLLM gateway
- Langfuse tracing
- OpenCLI source-sidecar pilot

But it should leave clean handoff notes in docs:

- gateway/tracing should consume the same run-state / governance truth files
- OpenCLI pilot should target one high-value dynamic source that is still awkward for plain polling

This keeps P1 closing cleanly without losing forward motion.

## Files to change

### Core logic

- `D:\GitHub\auto\src\auto_report\source_registry.py`
  - add priority scoring
  - add changedetection watch rows
  - add merged governance priority queue

### Artifact output

- `D:\GitHub\auto\src\auto_report\outputs\source_governance.py`
  - no major format rewrite needed; it can keep serializing the richer queue payload

### Dashboard rendering

- `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
  - add a new dashboard section for the merged governance priority queue
  - keep current grouped candidate sections

### Tests

- `D:\GitHub\auto\tests\test_source_registry.py`
  - verify queue grouping still works
  - verify changedetection watch rows gain operational fields
  - verify merged priority queue ordering
- `D:\GitHub\auto\tests\test_ops_dashboard.py`
  - verify the new priority queue section renders

### Docs

- `D:\GitHub\auto\V1升级方案.md`
  - mark `changedetection` and governance queue items complete only after implementation and verification
- optional supporting note:
  - `D:\GitHub\auto\交接备忘录.md`

## Data model changes

The `source_governance` payload should gain two new top-level keys:

- `changedetection_watch_list`
- `priority_queue`

Suggested shapes:

```json
{
  "changedetection_watch_list": [
    {
      "source_id": "anthropic-news",
      "watch_target": "https://www.anthropic.com/news",
      "priority_score": 78,
      "priority_label": "high",
      "reason": "enabled fragile listing with high-value category",
      "next_action": "Create a changedetection watch for this URL and store the watch reference."
    }
  ],
  "priority_queue": [
    {
      "source_id": "anthropic-news",
      "candidate_kind": "changedetection_watch",
      "priority_score": 78,
      "priority_label": "high",
      "reason": "enabled fragile listing with high-value category",
      "next_action": "Create a changedetection watch for this URL and store the watch reference."
    }
  ]
}
```

The exact field names may differ slightly, but the operational meaning should remain the same.

## Priority model

Use a transparent additive score, not ML, not heuristics hidden in templates.

Suggested scoring:

- base by `candidate_kind`
  - `manual_replace`: 90
  - `changedetection_watch`: 70
  - `rsshub_route`: 60
- category bonus
  - `ai-llm-agent`: +10
  - `ai-x-electronics`: +10
- enabled fragile source bonus
  - enabled + `fragile-listing` / `manual-watch`: +10
- stable source penalty
  - if source is already `stable-feed`, `stable-api`, or `stable-page`, do not include in the operational queue

Priority labels can be derived as:

- `high` for score >= 80
- `medium` for score >= 65
- `low` otherwise

This is enough for operations and easy to explain in code review.

## Non-goals

This batch intentionally does not:

- create changedetection watches automatically
- validate RSSHub routes over the network
- introduce databases or external state stores
- change the report generation chain
- implement LiteLLM / Langfuse / OpenCLI runtime integration

## Risks and mitigations

### Risk: over-designed governance model

Mitigation:

- keep the score small and deterministic
- avoid new abstractions unless reused twice

### Risk: dashboard bloat

Mitigation:

- add one strong operational section, not many new panels
- reuse current governance rendering helpers where possible

### Risk: stale candidate groups vs current config reality

Mitigation:

- tests should verify stabilized sources stay out of `changedetection_watch_list` and `priority_queue`
- this directly guards against regressions like previously stale `st-blog` governance rows

## Verification strategy

Minimum verification for this batch:

1. `tests/test_source_registry.py`
2. `tests/test_ops_dashboard.py`
3. `python -m pytest tests -q`
4. rebuild source governance artifact locally
5. rebuild ops dashboard locally

## P2 / P2.5 handoff

After this batch lands, the next logical sequence is:

1. `changedetection` checklist used operationally
2. governance priority queue validated by real maintenance use
3. then P2 gateway / tracing can attach to already-cleaner governance truth
4. OpenCLI pilot can target one source still stuck in fragile / dynamic territory

Recommended OpenCLI pilot target characteristics:

- high-value source
- weak or noisy static selectors
- likely browser-dependent or JS-dependent
- not already stabilized by RSS / JSON / structured page collection

That note is enough for now; implementation should wait until P1 closure is merged.
