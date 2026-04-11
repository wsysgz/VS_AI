# Dual-Track Publishing Design

> Date: 2026-04-12
> Scope: Phase 10 incremental close-out for `auto / reviewed` publishing

## Goal

Add an explicit publication mode so the repo can keep an automatically generated report and a manually reviewed report side by side, while preserving the current daily pipeline and public Pages surface.

## Why This Slice

The current V7 state matrix already marks channel roles as partly complete, but `auto / reviewed` dual-track publishing is still `not started`.

The repo already has:

- a single report package and rendering pipeline
- review queue generation for high-value topics
- public Pages generation from `data/reports` and `data/archives`
- workflow/manual entry points for normal runs and backfills

What is missing is the publishing contract itself. Right now every run writes to the same `latest-summary.*` and archive naming scheme, so a reviewed rerun would overwrite the auto track instead of coexisting with it.

## Design Summary

Introduce one explicit publication mode with two allowed values:

- `auto`
- `reviewed`

Mode affects four things:

1. report metadata and run status
2. output file naming
3. detail-link routing for channel notifications
4. Pages selection preference for the public latest view

## Runtime Contract

`publication_mode` becomes a first-class runtime field.

- default mode is `auto`
- manual local/CI reruns may switch to `reviewed`
- `summary_payload["meta"]["publication_mode"]` records the mode on the report itself
- `run-status.json` records the same mode for operational visibility

No third mode is added in this slice.

## Output Layout

Keep the legacy files for compatibility, but also emit track-specific files:

- `data/reports/latest-summary.md`
- `data/reports/latest-summary.json`
- `data/reports/latest-summary.html`
- `data/reports/latest-summary-auto.md|json|html`
- `data/reports/latest-summary-reviewed.md|json|html`

Archive outputs become mode-scoped:

- `data/archives/YYYY-MM-DD/<timestamp>-summary-auto.md|json|html`
- `data/archives/YYYY-MM-DD/<timestamp>-summary-reviewed.md|json|html`

Compatibility rule:

- the currently executed run still refreshes `latest-summary.*`
- the track-specific files preserve both tracks side by side

## Pages Preference Rule

Public Pages should prefer the reviewed version when both tracks exist for the same date.

Selection rule per date:

1. prefer `reviewed`
2. if no reviewed report exists, use the newest `auto`

This keeps the public surface stable while allowing later manual promotion without deleting the original auto record.

## Delivery Surface

Notification detail links should point to the exact track file:

- auto run links to `latest-summary-auto.md`
- reviewed run links to `latest-summary-reviewed.md`

Reviewed notifications and reports should also carry a visible reviewed label in their titles so operators can tell which track they are reading.

## CLI And Workflow Scope

This slice adds mode selection to the existing entry points instead of creating a separate reviewed-only toolchain.

- local CLI commands accept `--publication-mode`
- reusable workflows accept a `publication_mode` input
- scheduled mainline stays `auto`
- manual dispatch/backfill can choose `reviewed`

## Non-Goals

- no human approval UI
- no issue-to-report promotion automation
- no separate reviewed Pages domain
- no schema for reviewer identity or review notes
- no new notification channels

## Risks And Mitigations

- Risk: reviewed reruns still overwrite the public latest file
  - Mitigation: keep track-specific files and make Pages prefer reviewed explicitly
- Risk: existing tooling only knows `latest-summary.*`
  - Mitigation: preserve legacy files while adding new mode-scoped files
- Risk: operators cannot tell which track they are reading
  - Mitigation: add `publication_mode` to metadata, run status, titles, and Pages labels

## File Boundaries

- `src/auto_report/cli.py`
  - expose `--publication-mode`
- `src/auto_report/settings.py`
  - carry default publication mode from env
- `src/auto_report/app.py`
  - resolve mode, write track-specific outputs, build mode-aware detail URLs
- `src/auto_report/pipeline/run_once.py`
  - persist `publication_mode` into `run-status.json`
- `src/auto_report/outputs/pages_builder.py`
  - prefer reviewed track for public selection and expose mode labels
- `.github/workflows/collect-report.yml`
  - keep scheduled runs on `auto`, allow manual choice
- `.github/workflows/backfill-report.yml`
- `.github/workflows/reusable-report.yml`
- `.github/workflows/reusable-backfill.yml`
  - pass `publication_mode` into runtime env
- `tests/test_cli_smoke.py`
- `tests/test_run_once.py`
- `tests/test_pages_builder.py`
- `tests/test_settings.py`
- `tests/test_workflows.py`
  - prove the contract end to end

## Verification

- targeted CLI / run-once / pages / workflow tests
- `pwsh ./scripts/check-workflows.ps1`
- `$env:PYTHONPATH='src'; python -m pytest tests -q`

## Success Criteria

- `auto` and `reviewed` can coexist in `data/reports` and `data/archives`
- public Pages prefer reviewed when both tracks exist
- run status and report metadata clearly show the active publication mode
- scheduled workflow remains `auto` by default
- manual workflow/backfill can choose `reviewed`
