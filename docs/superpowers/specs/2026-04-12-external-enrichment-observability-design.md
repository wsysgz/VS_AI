# External Enrichment Observability Design

> Date: 2026-04-12
> Scope: Phase 9 close-out slice for external enrichment observability only

## Goal

Add run-scoped observability for external enrichment so operators can answer three questions from `run-status.json` and the private ops dashboard:

1. Did this run attempt external enrichment?
2. Did it succeed often enough to be useful?
3. Did the run stop further requests because the enrichment circuit opened?

This slice does not change public report payloads or public Pages output.

## Current State

The repository already supports:

- current-run support evidence from collected items
- opt-in external enrichment fetches for high-value topics
- a per-run max topic limit via `EXTERNAL_ENRICHMENT_MAX_SIGNALS`
- external enrichment enabled by default in reusable report/backfill workflows
- private ops dashboard reading `data/state/run-status.json`

What is still missing is operational visibility. Today we cannot reliably tell from `run-status.json` whether external enrichment was enabled, how much budget it used, how often it succeeded, or whether it stopped early after repeated failures.

## Design Summary

Keep observability in the existing run-status surface.

- `analysis.py` continues to wire external enrichment config into the intelligence layer.
- `intelligence.py` becomes the source of truth for enrichment runtime metrics.
- `run_once.py` stores those metrics under a new top-level `external_enrichment` block in `run-status.json`.
- `ops_dashboard.py` renders a new private-only external enrichment section from the same status payload.

No new metrics file is introduced, and no public report schema is expanded in this slice.

## Run-Status Schema

Add a new top-level object to `data/state/run-status.json`:

```json
{
  "external_enrichment": {
    "enabled": true,
    "max_signals": 2,
    "attempted": 2,
    "succeeded": 1,
    "failed": 1,
    "skipped": 1,
    "budget_used": 2,
    "success_rate": 0.5,
    "circuit_open": false,
    "reasons": [
      "empty-result: Topic A",
      "budget-exhausted: Topic C"
    ]
  }
}
```

Definitions:

- `enabled`: whether this run configured external enrichment on
- `max_signals`: configured attempt budget for high-value topics
- `attempted`: count of topics for which the external fetcher was actually invoked
- `succeeded`: count of attempted topics that returned at least one external evidence item
- `failed`: count of attempted topics that raised, timed out, or returned no useful evidence
- `skipped`: count of topics skipped because of threshold, budget exhaustion, or open circuit
- `budget_used`: equals the number of actual attempts in this slice
- `success_rate`: `succeeded / attempted`, `0.0` when `attempted == 0`
- `circuit_open`: whether the single-run circuit breaker opened
- `reasons`: concise operator-readable reasons for failed or skipped topics

## Circuit Breaker

This slice uses a single-run circuit breaker only.

Rules:

- Only high-value topics that are otherwise eligible for external enrichment participate.
- Two consecutive failed attempts open the circuit.
- Once the circuit is open, remaining eligible topics are skipped without invoking the fetcher.
- Any success resets the consecutive-failure counter to zero.

Failure reasons for attempted topics:

- `request-error`
- `timeout`
- `empty-result`

Skip reasons for eligible topics not attempted:

- `budget-exhausted`
- `circuit-open`
- `below-threshold`

The circuit is intentionally not persisted across runs in this slice.

## Dashboard Changes

The private ops dashboard gets one new section driven only by `run-status.json`.

It should show:

- enabled / disabled
- attempts, success, failed, skipped
- success rate
- max signals
- budget used
- circuit open / closed
- reason list from the latest run

This remains private-only and is not copied into `docs/`.

## File Boundaries

- `src/auto_report/pipeline/intelligence.py`
  - compute enrichment runtime metrics
  - apply circuit-breaker rules
  - return `external_enrichment` diagnostics alongside existing intelligence results
- `src/auto_report/pipeline/run_once.py`
  - allow `build_run_status()` to accept and persist `external_enrichment`
- `src/auto_report/app.py`
  - pass `external_enrichment` from the summary payload into `build_run_status()`
- `src/auto_report/outputs/ops_dashboard.py`
  - render the new enrichment observability section
- `tests/test_intelligence.py`
  - red/green coverage for metrics and circuit behavior
- `tests/test_run_once.py`
  - run-status persistence coverage
- `tests/test_ops_dashboard.py`
  - dashboard rendering coverage

## Non-Goals

- no public Pages changes
- no public report schema changes
- no cross-run circuit memory
- no historical enrichment trend charts
- no new standalone metrics file

## Risks And Mitigations

- Risk: empty external results look like success
  - Mitigation: treat empty result as failure and record `empty-result`
- Risk: observability logic leaks into public content
  - Mitigation: keep metrics only in `run-status.json` and private dashboard
- Risk: fetcher failures still waste time late in a run
  - Mitigation: open the circuit after two consecutive failures

## Verification Strategy

- targeted intelligence tests for metrics, reasons, and circuit opening
- targeted run-status test proving `external_enrichment` is persisted
- targeted dashboard test proving the new section renders
- full regression with `$env:PYTHONPATH='src'; python -m pytest tests -q`
