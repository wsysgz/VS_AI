# Source Governance Closure Design

**Date:** 2026-04-21
**Workspace:** `D:\GitHub\auto`

## Goal

Close the repo-local source governance loop without changing the main collection architecture:

1. turn approved lead reviews into safe, applyable source updates,
2. apply low-risk updates back into `config/sources/*.yaml`,
3. rebuild governance artifacts and review queue after apply,
4. expand the curated source pool with additional domestic and international sources that fit the existing collectors.

## Non-Goals

- No OpenCLI or browser runtime integration
- No GitHub Actions-first rollout
- No automatic promotion of raw discovery leads into production sources
- No new collector type beyond existing RSS / websites / GitHub support
- No external changedetection.io provisioning in this batch

## Desired End State

After this batch, the repo should support a controlled local loop:

`source-lead-review-status.json -> candidate-updates.json -> apply-source-updates -> config/sources/*.yaml -> build-source-governance -> build-review-queue`

The loop is intentionally conservative:

- `official_feed` updates can be applied automatically only when they target a known source id and expose a direct feed URL.
- `validated_listing` updates can be applied automatically only when the source is already a known website source.
- `changedetection` updates can be applied automatically only as local governance metadata updates for known website sources.
- `rsshub` updates remain review-only for now because the repo does not yet carry a single verified RSSHub base contract.
- unknown / net-new leads remain in `candidate-updates.json` for human review even when approved.
- high-priority `changedetection_watch` items are tracked in a repo-local watch registry and executed by a repo-local watch runner rather than a third-party changedetection service.

## Governance Closure Extension

### 1. Local Watch Registry

Add a repo-local registry at:

- `out/source-governance/changedetection-watch-registry.json`

This file becomes the operational truth for local watch progression. It is distinct from the source config truth and from the governance queue snapshot.

Each registry item should carry:

- `source_id`
- `watch_target`
- `priority_score`
- `priority_label`
- `status`
- `note`
- `watch_url`
- `watch_reference`
- `next_action`
- `updated_at`

Supported statuses for this batch:

- `planned`
- `active_local`
- `deferred`
- `blocked`

New queue items default to `planned`. Existing registry state must be preserved on rebuild.

### 2. Local Watch Runner

Add a repo-local runner that:

- loads active watch entries from `changedetection-watch-registry.json`
- reuses existing website source selectors and fetch logic
- stores a baseline / seen-entry state in an artifact file
- emits a latest run result artifact with changed / unchanged / blocked counts

This runner is intentionally local-first and does not depend on Docker, paid SaaS, or browser extensions.

### 3. candidate-updates Practical Closure

`candidate-updates.json` should become the actionable queue for two update kinds:

- `source_update`
- `watch_update`

For `watch_update`, the command should surface only actionable registry items, primarily `planned` high-priority local watches that can be promoted into `active_local`.

For `source_update`, already-applied updates should be suppressed from `candidate-updates.json` so the file stays close to executable work instead of repeating solved items.

### 4. apply-source-updates Practical Closure

`apply-source-updates` should support both:

- applying safe source config mutations
- promoting actionable changedetection registry rows

For watch updates in this batch, applying means:

- create or update the registry entry
- move `planned -> active_local`
- preserve `active_local` / `deferred` / `blocked`
- record `updated_at`

This batch does **not** create third-party changedetection.io watches. The local runner replaces that dependency.

## Architecture

### 1. Lead Update Classification

`src/auto_report/pipeline/review_queue.py` remains the place that turns review status into `candidate-updates.json`, but the output becomes more operational:

- prefer the already-computed `meta.source_id` instead of weak keyword inference
- mark whether an update is locally applyable
- emit a blocking reason for updates that still require human mapping or remote validation
- keep `candidate-updates.json` as the operator-facing queue

### 2. Source Update Apply Layer

Add a dedicated apply layer that owns config mutation:

- read `out/review-queue/candidate-updates.json`
- select only `apply_ready=true` updates
- apply them to the correct source config file
- write an execution summary artifact
- rebuild governance and review queue artifacts

This logic lives outside the collectors so the collection chain stays unchanged.

### 3. Safe Apply Rules

#### `official_feed`

- allowed only when `source_id` is known
- move or upsert the source into `config/sources/rss.yaml`
- remove the same `source_id` from `websites.yaml` / `github.yaml` if present
- preserve stable operator fields such as `category_hint`, `max_items`, and include/exclude title filters when they exist

#### `validated_listing`

- allowed only when `source_id` already exists as a website source
- update the existing website source metadata to the validated listing state
- preserve selectors, title filters, and `max_items`

#### `changedetection`

- allowed only when `source_id` already exists as a website source
- update only local governance metadata, not an external watch id
- mark the source with explicit changedetection-style fields so it stays visible in governance output

#### `rsshub`

- do not auto-apply in this batch
- keep as approved-but-blocked queue items until a repo-level RSSHub base URL / validation rule is introduced

### 4. Curated Source Expansion

Add a small set of low-risk sources that fit current collectors.

#### Website sources

- `zhipu-news` (domestic AI / Agent news listing)
- `renesas-blog` (international AI x electronics listing)
- `edge-impulse-blog` (international edge AI listing)

#### GitHub curated repositories

AI / agent:
- `microsoft/autogen`
- `openai/openai-agents-python`
- `mistralai/mistral-inference`
- `QwenLM/Qwen3`
- `modelscope/ms-swift`
- `deepseek-ai/DeepEP`

AI x electronics:
- `espressif/esp-dl`
- `Seeed-Studio/SSCMA-Micro`

These additions are intentionally chosen because they are official, current, and already match existing RSS / website / GitHub collectors.

## Files

### Code

- Modify: `D:\GitHub\auto\src\auto_report\pipeline\review_queue.py`
- Create: `D:\GitHub\auto\src\auto_report\pipeline\source_updates.py`
- Create: `D:\GitHub\auto\src\auto_report\pipeline\watch_runner.py`
- Modify: `D:\GitHub\auto\src\auto_report\outputs\source_governance.py`
- Modify: `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`

### Config

- Modify: `D:\GitHub\auto\config\sources\websites.yaml`
- Modify: `D:\GitHub\auto\config\sources\github.yaml`

### Tests

- Modify: `D:\GitHub\auto\tests\test_review_queue.py`
- Create: `D:\GitHub\auto\tests\test_source_updates.py`
- Create: `D:\GitHub\auto\tests\test_watch_runner.py`
- Modify: `D:\GitHub\auto\tests\test_source_governance_output.py`
- Modify: `D:\GitHub\auto\tests\test_ops_dashboard.py`
- Modify: `D:\GitHub\auto\tests\test_cli_smoke.py`
- Modify: `D:\GitHub\auto\tests\test_settings.py`

### Docs

- Create: `D:\GitHub\auto\docs\superpowers\specs\2026-04-21-source-governance-closure-design.md`
- Create: `D:\GitHub\auto\docs\superpowers\plans\2026-04-21-source-governance-closure.md`

## Verification

Minimum verification for this batch:

1. targeted unit tests for review queue updates
2. targeted unit tests for source update apply logic
3. CLI smoke test for the new command
4. settings/config regression tests for added sources
5. full `python -m pytest tests -q`
