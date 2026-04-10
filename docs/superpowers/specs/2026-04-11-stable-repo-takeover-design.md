# Stable Repo Takeover Design

**Date:** 2026-04-11  
**Workspace:** `D:\GitHub\auto`  
**Repo:** `wsysgz/VS_AI`

## Goal

Complete a stable takeover of the repository by:

- consolidating formal documentation while preserving audit materials
- removing redundant or accidental repository clutter
- fixing hidden engineering and delivery risks without unrelated refactors
- restoring and proving daily `07:00` Beijing-time delivery to WeChat, Feishu, and Telegram
- validating locally first, then pushing exactly once after end-to-end verification

## Constraints

- Preserve `docs/superpowers/` as audit material and do not treat it as cleanup target.
- Keep the daily user-facing schedule as one comprehensive report around Beijing `07:00`.
- Do not rely on "no exception thrown" as proof of notification success.
- Favor incremental hardening over broad architectural rewrites.
- Push only after local verification and real-channel validation succeed.

## Non-Goals

- No large-scale refactor of the collection, analysis, or rendering architecture.
- No redesign of report format beyond what is required for stable delivery.
- No removal of historical plans, specs, handoff notes, or upgrade records.
- No expansion into new product scope such as email, MCP, weekly/monthly reports, or bilingual output.

## Current Context Summary

The repository already contains:

- a daily report pipeline spanning collection, AI analysis, rendering, archiving, and multi-channel delivery
- formal entry docs such as `README.md` and `docs/HANDOFF.md`
- secondary docs including `docs/USER_GUIDE.md`, `docs/TECHNICAL_GUIDE.md`, `docs/ARCHITECTURE.md`, and `docs/push-channels-guide.md`
- audit/history material in `docs/superpowers/`
- generated site/report artifacts in `docs/archives/`, `docs/index.html`, `data/`, and `site-dist/`
- known delivery concerns, especially previous failure to reach WeChat and Telegram

The takeover should treat the existing system as a running product with drift, not as a blank-slate codebase.

## Document Governance Design

### Formal document tiers

Use three tiers and keep responsibilities clear:

1. **Primary entry points**
   - `README.md`
   - `docs/HANDOFF.md`

2. **Formal operational docs**
   - `docs/USER_GUIDE.md`
   - `docs/TECHNICAL_GUIDE.md`
   - `docs/ARCHITECTURE.md`
   - `docs/push-channels-guide.md`

3. **Audit materials**
   - everything under `docs/superpowers/`
   - upgrade and historical records such as `docs/upgrade-plan-v6/`

### Cleanup rules

Delete only material that matches at least one of these conditions:

- duplicated guidance that adds no new information and conflicts with the chosen formal entry points
- temporary test outputs or one-off debugging artifacts
- accidental copies, redundant generated directories, or stale helper notes with no operational value
- documentation that points to obsolete working directories or delivery rules and is superseded by formal docs

Do **not** delete:

- `docs/superpowers/**`
- handoff and upgrade records with audit value
- report archives needed for tracing published output
- generated assets that are still part of the intended Pages or report publishing model unless the build flow is first corrected

### Desired outcome

After cleanup, a new maintainer should be able to answer these questions without conflicting docs:

- Where do I start?
- How does the system run?
- How are the three delivery channels configured and verified?
- Which files are formal docs and which are audit history?

## Delivery Hardening Design

Treat delivery as a four-layer system and validate each layer explicitly.

### Layer 1: Configuration

Verify consistency across:

- `.env.example`
- `settings.py`
- runtime environment access in application code
- GitHub Actions secret wiring
- documentation describing each channel

Key questions:

- Are variable names consistent for all three channels?
- Does each trigger mode set `AUTO_PUSH_ENABLED` correctly?
- Are there misleading docs that encourage broken setups?

### Layer 2: Application Flow

Verify the report pipeline actually reaches all intended branches:

- `run_once`
- `render-and-push`
- channel-specific notification builders
- status recording in `run-status.json`

Key risks:

- false positives where `pushed=true` even if one or more channels failed
- skipped channels due to wrong AI/config/delivery gating
- incorrect summary/full-text routing per channel

### Layer 3: Integration Adapters

Validate each delivery adapter independently:

- PushPlus / WeChat
- Telegram
- Feishu

Each adapter should provide reliable evidence for:

- configuration present or missing
- request attempted or skipped
- success response shape
- failure reason with useful detail

The system should make it easy to distinguish:

- bad credentials
- inactive chat/bot/session state
- local network reachability problems
- channel formatting or payload issues

### Layer 4: Acceptance

Delivery is considered fixed only if all of the following are true:

- local end-to-end run completes
- the generated report is correct
- one real validation message reaches each configured channel
- the repository is pushed once
- the remote workflow still preserves the Beijing `07:00` schedule and three-channel delivery behavior

## Hidden-Risk Remediation Design

Focus only on hidden risks that materially threaten operation or maintainability.

### Risk categories

1. **Delivery risks**
   - miswired env vars
   - false success status
   - broken workflow inputs
   - silent exception swallowing

2. **Runtime risks**
   - local-only behavior that fails in CI
   - unstable file paths or generated artifact assumptions
   - data/output paths polluting repository state

3. **Maintainability risks**
   - conflicting docs
   - unclear authority between docs
   - no reliable diagnostic path for notification failures

4. **Publishing risks**
   - generated content overwriting maintained docs
   - temporary files lingering in the repo
   - accidental inclusion of local diagnostics in versioned state

5. **External dependency risks**
   - Telegram network access issues
   - PushPlus channel activation/state problems
   - Feishu permission or bot state problems

### Remediation rules

- Prefer targeted fixes over broad rewrites.
- Add or update regression tests for each confirmed bug.
- Add diagnostics where the system currently hides failure state.
- Keep observable behavior aligned with the current product promise: one daily report, three delivery channels.

## Execution Order

1. Review all formal and untracked docs.
2. Classify docs into keep, merge, trim, or delete.
3. Clean temporary or redundant repository artifacts.
4. Reproduce delivery behavior using current real configuration.
5. Trace failures through configuration, application, adapter, and workflow layers.
6. Add failing tests for confirmed bugs.
7. Implement minimal fixes.
8. Run local test suite and local end-to-end workflow.
9. Perform real-channel validation to WeChat, Feishu, and Telegram.
10. Review remote scheduling and workflow behavior.
11. Push once after all gates pass.

## Verification Plan

Verification must include both code-level and real-world checks.

### Local verification

- targeted tests for newly fixed issues
- full `pytest` run
- one local pipeline run with actual configuration
- inspection of generated outputs and `data/state/run-status.json`

### Real delivery verification

- PushPlus message received in WeChat
- Feishu message received in target chat
- Telegram message received in target chat

### Remote verification

- verify pushed branch and workflow state
- confirm cron remains `0 23 * * *`
- confirm the workflow still routes scheduled runs to actual pushes

## Stop Conditions

Implementation must pause if any of these occurs:

- a channel requires manual re-authorization that cannot be completed from repository-side fixes
- Telegram fails due to environmental network blocking and evidence shows code/config are already correct
- cleanup would remove material with audit value or unclear operational coupling
- remote workflow behavior conflicts with local assumptions in a way that requires a product decision

In those cases, the repository-side work should still be completed and the remaining external blocker should be documented with concrete evidence.

## Acceptance Criteria

The takeover is complete only when:

- formal documentation is coherent and non-redundant
- audit materials are preserved
- repository clutter is reduced without damaging required history or generated outputs
- confirmed hidden risks are fixed
- local tests pass
- local end-to-end execution passes
- WeChat, Feishu, and Telegram each receive a real validation message
- the remote repository is pushed once
- daily Beijing `07:00` delivery remains intact

## Open Questions Resolved

- `docs/superpowers/` is preserved as audit material.
- Real three-channel validation is allowed before final push.
- The preferred strategy is stable takeover rather than broad restructuring.
