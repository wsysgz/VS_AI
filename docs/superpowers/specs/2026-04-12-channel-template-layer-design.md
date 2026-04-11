# Channel Template Layer Design

> Date: 2026-04-12
> Scope: Phase 10 incremental close-out for channel-specific delivery templates

## Goal

Make the delivery layer explicitly channel-shaped instead of relying on partially shared notification templates.

This slice keeps a single semantic brief while formalizing three delivery profiles:

- PushPlus / WeChat: short
- Feishu: medium
- Telegram: long

## Why This Slice

The current V7 roadmap says Phase 10 should continue by splitting the channel template layer before starting `auto / reviewed` dual-track publishing.

The repo already has:

- one shared executive brief builder
- PushPlus short-text delivery
- Telegram long-form delivery
- Feishu delivery transport

What remains ambiguous is the template boundary itself. Without an explicit layer, docs and code drift easily, and later publication modes will have to untangle delivery shape from content policy at the same time.

## Design Summary

Keep `compose_executive_brief()` as the only semantic source, and make each channel renderer explicit.

- `render_pushplus_notification()`
  - one-line judgment
  - 2-3 mainlines
  - risk note
  - detail link
- `render_feishu_notification()`
  - one-line judgment
  - executive summary
  - mainlines
  - action items
  - risk note
  - detail link
- `render_telegram_notification()`
  - keep the current long-form shape
  - executive summary
  - mainlines
  - topic list
  - short-term watchlist
  - risk note
  - detail link

## Boundaries

This slice includes:

- renderer naming and channel responsibility cleanup
- app-level wiring to the explicit channel renderers
- tests proving short / medium / long separation
- doc updates in maintainer-facing guides
- status-matrix wording updates for Phase 10 progress alignment

This slice does not include:

- `auto / reviewed` dual-track publishing
- new delivery channels
- message cards, rich blocks, or HTML channel payloads
- review queue logic changes
- workflow schedule changes

## File Plan

- `src/auto_report/outputs/renderers.py`
  - add explicit PushPlus renderer entrypoint
  - keep shared brief reuse
- `src/auto_report/app.py`
  - call explicit channel renderers
- `tests/test_renderers.py`
  - assert PushPlus short shape
- `tests/test_run_once.py`
  - keep delivery integration expectations aligned
- `README.md`
  - update product promise wording
- `docs/USER_GUIDE.md`
  - update operational description of each channel
- `docs/ARCHITECTURE.md`
  - describe renderer layer as short / medium / long
- `docs/OPS_RUNBOOK.md`
  - align handoff wording with current delivery surface
- `docs/push-channels-guide.md`
  - make channel output contracts explicit
- `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`
  - reduce ambiguity in the Phase 10 channel-template row

## Verification

- targeted renderer tests
- targeted run-once delivery tests
- full `pytest`

## Success Criteria

- code has explicit PushPlus / Feishu / Telegram template entrypoints
- docs no longer say Feishu and Telegram share the same “full report” shape
- Phase 10 progress notes reflect that channel roles are now short / medium / long, while richer per-channel families remain future work
