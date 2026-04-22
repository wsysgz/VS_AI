# P3-B Feishu Ops Desk Design

**Date:** 2026-04-22
**Workspace:** `D:\GitHub\auto`

## Goal

Define the first formal `P3-B` design for a Feishu multidimensional-table ops desk that:

1. serves the user's own daily operations first,
2. presents an at-a-glance dashboard before drill-down handling,
3. uses Feishu as an operations + approval surface,
4. keeps repo JSON / config as the only source of truth,
5. allows limited writeback only for status-class collaboration data.

This design builds on the current local sidecar foundation:

- Feishu report doc
- governance sheet
- governance task list

and turns that foundation into a structured, reviewable `P3-B` plan.

## User Decisions Already Made

- Primary user: the repo owner’s own daily operations, not a generic shift team first
- Home page style: dashboard-first, then drill into detail views
- Preferred module organization: grouped by business area, not by process phase
- Feishu writeback scope:
  - allowed: approval status + delivery verification status
  - not allowed: direct source config edits or execution-state promotion
- Repo remains the only production truth source

## Non-Goals

- No direct editing of `config/sources/*.yaml` from Feishu
- No direct execution trigger from Feishu that bypasses local CLI verification
- No GitHub Actions dependency for the Feishu ops desk
- No first-batch migration to Feishu “application mode” as the primary interface
- No replacement of `run-status.json`, `source-governance.json`, or review-queue artifacts as repo truth
- No attempt to make Feishu the scheduler or orchestration layer

## Desired End State

After `P3-B` first rollout, the repo should support this operator loop:

`repo truth JSON -> local sidecar sync -> Feishu ops desk -> limited status edits -> local pull-back sync -> repo status JSON`

The operator experience should answer three daily questions in under one minute:

1. what do I need to look at today?
2. what do I need to approve today?
3. what delivery / governance status needs confirmation today?

The repo should still own all canonical logic:

- source registry and governance
- review queue generation
- candidate update generation
- delivery execution
- report rendering and publication

Feishu should become the front-end operating surface, not the back-end rules engine.

## Why This Direction

Current repo state already supports enough local-first artifacts to justify a formal ops desk:

- `data/state/run-status.json`
- `out/source-governance/source-governance.json`
- `out/review-queue/source-lead-review-status.json`
- `out/review-queue/candidate-updates.json`
- `data/state/feishu-sidecar.json`

Recent `P3-A` closure also makes Feishu the most important human-facing operating surface:

- Feishu static card path has been manually verified
- Feishu-only validation command now exists
- Feishu doc / governance sheet / governance tasks are already synced locally

This means `P3-B` should not start from a blank sheet; it should formalize and extend the existing sidecar bridge.

## Product Shape

### 1. Overall Shape

The first `P3-B` batch should be a **standard ops desk**:

- dashboard-first landing page
- four business-area modules
- four corresponding tables / views
- limited writable fields for collaboration status only

This should feel like a daily operator cockpit, not a raw exported data sheet.

### 2. Home Dashboard

The home page should be an operator-first dashboard, not a data wall.

It should contain:

#### Top summary cards

- latest auto delivery status
- latest reviewed delivery status
- blocked governance count
- pending approval count
- candidate update count
- fallback / verification reminder count

#### Four business modules

1. `Feishu Delivery`
2. `Source Governance`
3. `Approval Collaboration`
4. `Candidate Updates`

Each module should show:

- 2-4 headline metrics
- the next most actionable records
- a clear drill-down entry into its detailed table or saved view

#### Bottom strip

- latest operator notes / annotations
- recent changes
- direct jump links

This preserves the chosen “dashboard first, then drill down” interaction model.

## Data Model

### Table 1: Source Governance Main Table

Purpose: give a stable, mostly read-only operational view of high-value governance work.

Primary source:

- `out/source-governance/source-governance.json`

Recommended fields:

- `source_id`
- `category_hint`
- `priority_label`
- `priority_score`
- `candidate_kind`
- `stability_tier`
- `watch_strategy`
- `automation_ready`
- `next_action`
- `replacement_target`
- `url`
- `updated_at`

Primary views:

- `High Priority Queue`
- `Blocked Sources`
- `Manual Review`
- `Changedetection Candidates`
- `Replacement Candidates`

Write policy:

- read-only in first batch

Reason:

This table is the operational map. It should remain generated from repo truth and not become the editing surface.

### Table 2: Source Lead Review Approval Table

Purpose: give the operator a clean approval queue for discovery/governance leads.

Primary source:

- `out/review-queue/source-lead-review-status.json`

Recommended fields:

- `lead_key`
- `keyword`
- `title`
- `bucket`
- `priority_label`
- `priority_score`
- `status`
- `note`
- `updated_at`

Writable fields in first batch:

- `status`
- `note`

Allowed status values:

- `pending`
- `approved`
- `rejected`
- `deferred`

Primary views:

- `Pending Review`
- `Approved`
- `Deferred`
- `Recently Updated`

Writeback target:

- `out/review-queue/source-lead-review-status.json`

Reason:

This is the cleanest and safest first writable collaboration surface already present in the repo.

### Table 3: Delivery Audit Table

Purpose: record human validation of the delivery surface, especially Feishu card quality and fallback observation.

Primary source:

- `data/state/run-status.json`
- optional local review state JSON introduced by this batch

Recommended fields:

- `generated_at`
- `publication_mode`
- `risk_level`
- `feishu_status`
- `feishu_message_id`
- `pushplus_status`
- `telegram_status`
- `card_verified`
- `fallback_observed`
- `delivery_note`
- `reviewer`
- `trace_url`

Writable fields in first batch:

- `card_verified`
- `fallback_observed`
- `delivery_note`

Primary views:

- `Latest Delivery`
- `Needs Verification`
- `Fallback Observed`
- `Reviewed Track Checks`

Writeback target:

- `data/state/delivery-audit-review.json`

Reason:

This keeps operator annotations separate from generated run-state truth while still making them first-class repo data.

### Table 4: Candidate Updates Table

Purpose: show which approved items are waiting for real config application.

Primary source:

- `out/review-queue/candidate-updates.json`

Recommended fields:

- `update_key`
- `source_id`
- `update_type`
- `summary`
- `apply_ready`
- `blocking_reason`
- `validation_mode`
- `generated_at`

Primary views:

- `Ready To Apply`
- `Blocked By Evidence`
- `Watch Updates`
- `Source Updates`

Write policy:

- read-only in first batch

Reason:

The user chose not to let Feishu directly drive execution-state promotion yet. This table should surface work without becoming the execution switch.

## Feishu Writeback Boundary

### Allowed Writeback

Only two categories are writable from Feishu in the first batch:

1. approval collaboration status
2. delivery verification status

That means:

- yes: `approved / rejected / deferred / note`
- yes: `card_verified / fallback_observed / delivery_note`
- no: direct source config mutations
- no: direct candidate-update execution approval
- no: workflow or publish toggles

### Writeback Principle

Feishu edits should update repo-side **status files**, never repo-side **execution config** in the first batch.

This preserves the repo as the source of truth while still making Feishu operationally useful.

## Sync Model

### Repo -> Feishu

The sidecar should continue to own outward sync:

- governance JSON -> governance main table
- review status JSON -> approval table
- candidate updates JSON -> candidate updates table
- run status + review overlay -> delivery audit table

### Feishu -> Repo

A new local pull-back sync should:

- read only explicitly writable columns
- validate allowed values
- update only the matching repo status JSON
- preserve timestamps / conflict notes

### Suggested CLI shape

First-batch command shape should stay local-first and explicit:

- extend `sync-feishu-workspace`
- or introduce a sibling command such as:
  - `sync-feishu-ops-desk`
  - `pull-feishu-ops-status`

Recommendation:

- keep one outward sync entrypoint for building/updating the Feishu workspace
- add one separate inward sync entrypoint for pulling writable statuses back into repo JSON

This avoids mixing “push data out” and “pull edits back” in one opaque command.

## Views And Navigation

### Home Navigation

The dashboard should link into four stable destinations:

- `Delivery`
- `Governance`
- `Approvals`
- `Candidate Updates`

### Delivery Module

Summary cards:

- latest auto push result
- latest reviewed push result
- Feishu verification pending count

Action links:

- latest delivery record
- records missing `card_verified`
- records with `fallback_observed=true`

### Governance Module

Summary cards:

- blocked count
- high priority count
- manual review count

Action links:

- blocked sources
- top priority queue
- watch candidates

### Approval Module

Summary cards:

- pending approvals
- approved today
- deferred backlog

Action links:

- pending review view
- recently updated view

### Candidate Updates Module

Summary cards:

- total updates
- ready count
- blocked count

Action links:

- ready-to-apply
- blocked-by-evidence

## Suggested Rollout Phases

### Phase B1: Formalize The Desk

- add the design-backed table definitions
- normalize current sidecar output into the four-table structure
- keep governance and candidate update tables read-only

### Phase B2: Add Safe Writeback

- allow approval status edits
- allow delivery audit status edits
- add local pull-back sync
- keep repo truth authoritative

### Phase B3: Add Feishu Views / Dashboard Polish

- optimize saved views
- add dashboard grouping and navigation
- tune operator-first field ordering and labels

### Deferred

- Feishu application-mode front-end
- execution-state promotion from Feishu
- config mutation from Feishu
- workflow triggers from Feishu

## Failure Handling

### 1. Missing Feishu sidecar state

If the local sidecar state is missing, rebuild the Feishu workspace from repo truth instead of treating Feishu as canonical.

### 2. Feishu edit conflicts

If a writable record in Feishu no longer maps cleanly to repo truth:

- do not force overwrite
- record a conflict note
- leave repo truth unchanged

### 3. Invalid writable values

If a Feishu cell contains an unsupported status:

- reject the writeback
- surface it in the local pull-back summary
- keep existing repo JSON unchanged

### 4. GitHub Actions runtime

Keep the sidecar local-only in first batch:

- no Feishu ops desk sync inside GitHub Actions
- no remote workflow dependency for the operator desk

## Verification

Minimum verification for this design’s first implementation batch:

1. unit tests for table export payload generation
2. unit tests for writable-field filtering
3. unit tests for Feishu status pull-back validation
4. local dry-run sync showing repo -> Feishu mapping
5. local dry-run pull-back showing Feishu -> repo status-only mapping

Operational acceptance:

1. operator can open home dashboard and identify today’s priorities in under one minute
2. one approval status change in Feishu can be pulled back into repo JSON safely
3. one delivery audit note in Feishu can be pulled back into repo JSON safely
4. no direct config file mutation happens from Feishu edits

## Files Expected In The Future Implementation

### Likely code touchpoints

- `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- `D:\GitHub\auto\src\auto_report\app.py`
- `D:\GitHub\auto\src\auto_report\cli.py`
- `D:\GitHub\auto\src\auto_report\outputs\source_governance.py`
- `D:\GitHub\auto\src\auto_report\pipeline\review_queue.py`
- `D:\GitHub\auto\src\auto_report\pipeline\run_once.py`

### Likely state / artifact files

- existing: `D:\GitHub\auto\data\state\feishu-sidecar.json`
- existing: `D:\GitHub\auto\out\review-queue\source-lead-review-status.json`
- existing: `D:\GitHub\auto\out\review-queue\candidate-updates.json`
- new: `D:\GitHub\auto\data\state\delivery-audit-review.json`
- optional new: `D:\GitHub\auto\out\feishu-ops\*.json` for export snapshots

## External Reference Direction

This design direction is consistent with current Feishu product patterns:

- multidimensional tables as a shared operations surface
- dashboards for operator summary first, detail later
- automation / application-mode as later-stage enhancement, not first-batch dependency

Useful official references reviewed for direction:

- Feishu multidimensional table use cases and dashboard-style operation pages
- Feishu application-mode direction for turning tables into business front-ends
- Feishu automation-oriented examples for follow-up expansion
