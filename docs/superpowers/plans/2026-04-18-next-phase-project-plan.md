# Next Phase Project Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move VS_AI from “P1 basically closed + local P2 primitives landed” into a controlled P2 rollout, with GitHub Actions remaining the production path and `lark-cli` staying local-only.

**Architecture:** Keep the current `collect -> analyze -> render -> publish` pipeline intact. Treat the current repo as having three layers: production pipeline (`run-once` + GitHub Actions), governance helper layer (`source_governance` + discovery/search artifacts), and local collaboration sidecars (`lark-cli` / Feishu sync). Advance P2 by turning existing local contracts into verified remote operating behavior before adding new platform dependencies like LiteLLM or Langfuse.

**Tech Stack:** Python, GitHub Actions YAML, pytest, existing LLM stage routing, existing Feishu API integration, local `lark-cli` sidecar.

---

## Current State Snapshot

- P1 is functionally closed except for RSSHub / remote validation tail work, especially `anthropic-news`.
- P2-A local groundwork is already in repo truth:
  - helper-stage env keys exist in `src/auto_report/settings.py`
  - `pre_filter` is routed through `stage="prefilter"` in `src/auto_report/pipeline/scoring_llm.py`
  - discovery/search helper artifacts exist and are surfaced in governance/dashboard flows
  - GitHub Actions now supports unified provider env/secret wiring, but remote variables are not yet treated as fully rolled out
- Feishu-first local collaboration is now available, but intentionally isolated from GitHub Actions:
  - production Feishu push remains the built-in API path
  - `lark-cli` sidecar is local-only and auto-skips when `GITHUB_ACTIONS=true`

## File Map

- Read / update as roadmap truth:
  - `D:\GitHub\auto\V1升级方案.md`
  - `D:\GitHub\auto\AI对接手册.md`
  - `D:\GitHub\auto\交接备忘录.md`
- Existing plans to execute or refine:
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-github-actions-provider-rollout.md`
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-remote-provider-enable-checklist.md`
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-p2-ai-routing.md`
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-discovery-search-helper.md`
- Production verification sources:
  - `D:\GitHub\auto\data\state\run-status.json`
  - `D:\GitHub\auto\out\source-governance\source-governance.json`
  - `D:\GitHub\auto\.github\workflows\`

## Recommended Execution Order

### Task 1: Finish P2-A with remote validation, not more local abstraction

**Why now:** The repo already has the local routing and workflow contract. The missing step is proving the remote operating model with GitHub Actions.

**Files:**
- Reuse: `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-github-actions-provider-rollout.md`
- Reuse: `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-remote-provider-enable-checklist.md`
- Verify: `D:\GitHub\auto\.github\workflows\collect-report.yml`
- Verify: `D:\GitHub\auto\.github\workflows\reusable-analyze.yml`
- Verify: `D:\GitHub\auto\.github\workflows\reusable-report.yml`

- [ ] **Step 1: Confirm the repo still passes the local workflow guard**

Run:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
```

Expected: PASS.

- [ ] **Step 2: Validate current local stage-routing behavior before touching remote settings**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_scoring_llm.py tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 3: Configure remote repository variables/secrets using the existing checklist**

Use the contract from `2026-04-18-remote-provider-enable-checklist.md`.

Recommended first remote activation:

```text
AI_PROVIDER=deepseek
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat

ANALYSIS_AI_PROVIDER=deepseek
ANALYSIS_AI_BASE_URL=https://api.deepseek.com
ANALYSIS_AI_MODEL=deepseek-chat

SUMMARY_AI_PROVIDER=minimax_svips
SUMMARY_AI_BASE_URL=https://api.svips.org/v1
SUMMARY_AI_MODEL=MiniMax-M2.7

FORECAST_AI_PROVIDER=deepseek
FORECAST_AI_BASE_URL=https://api.deepseek.com
FORECAST_AI_MODEL=deepseek-chat
```

- [ ] **Step 4: Run one manual GitHub Actions validation with pushes disabled**

Workflow input recommendation:

```text
push_enabled=false
publication_mode=reviewed
reviewer=codex
review_note=p2-a remote validation
```

Expected: remote pipeline passes without relying on `lark-cli`.

- [ ] **Step 5: Inspect the resulting run status**

Check:

```text
stage_status.analysis == ok
stage_status.summary == ok
stage_status.forecast == ok
ai_metrics.stage_breakdown.summary.provider == minimax_svips
delivery_results.skipped_channels contains push channels for validation run
```

- [ ] **Step 6: Mark P2-A remote validation complete in roadmap docs**

Update only after fresh evidence lands.

### Task 2: Keep P1 residual work narrow and operational

**Why now:** P1 should not keep expanding. Only the unresolved tail items should remain active.

**Files:**
- Verify: `D:\GitHub\auto\out\source-governance\source-governance.json`
- Update: `D:\GitHub\auto\V1升级方案.md`
- Update: `D:\GitHub\auto\交接备忘录.md`

- [ ] **Step 1: Re-check the current governance queue**

Run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-source-governance
```

Expected: artifact refreshes successfully.

- [ ] **Step 2: Confirm whether `anthropic-news` is still the only meaningful P1 blocker**

Inspect:

```text
out/source-governance/source-governance.json
data/state/run-status.json
```

Expected: most governance work is in routine ops mode, not roadmap-blocking mode.

- [ ] **Step 3: Keep the P1 tail list explicit and small**

Retain only items like:

```text
- anthropic-news remote / external validation
- any RSSHub candidate that still lacks a verified route
```

Do not reopen already-closed dashboard / governance structure work.

### Task 3: Decide whether discovery/search leads should enter a stronger operations loop

**Why now:** The discovery/search helper already exists. The next question is productization, not invention.

**Files:**
- Verify: `D:\GitHub\auto\src\auto_report\outputs\source_governance.py`
- Verify: `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
- Optional follow-on plan target: `D:\GitHub\auto\docs\superpowers\plans\`

- [ ] **Step 1: Review the current leads surfaced in governance**

Inspect:

```text
discovery_search
official_feed_leads
rsshub_leads
changedetection_leads
```

- [ ] **Step 2: Make a product decision, not an implementation guess**

Choose one of:

```text
A. Keep leads advisory-only
B. Promote verified leads into a review queue / human approval flow
C. Promote a narrow subset into executable governance actions
```

Recommended next move: **B**.

- [ ] **Step 3: If promoted, create a dedicated plan for “verified lead -> approved source update”**

Do not mix that work into LiteLLM or tracing tasks.

### Task 4: Start P2-B only after P2-A remote behavior is proven

**Why now:** LiteLLM is useful, but only after the repo’s current stage-routing contract is operationally trusted.

**Files:**
- Update next: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Update next: `D:\GitHub\auto\src\auto_report\settings.py`
- Update next: `D:\GitHub\auto\README.md`
- Future plan target: `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-litellm-gateway-rollout.md`

- [ ] **Step 1: Define the gateway operating mode**

Decide explicitly:

```text
direct provider mode stays supported
gateway mode is opt-in
remote rollout starts with local-first validation
```

- [ ] **Step 2: Constrain the first LiteLLM batch**

First batch should only do:

```text
- direct vs gateway toggle
- base URL / auth contract
- no prompt rewrites
- no fallback graph redesign
```

- [ ] **Step 3: Defer rollout until after local + remote validation criteria are written**

No implementation before a dedicated LiteLLM plan exists.

### Task 5: Keep Langfuse and OpenCLI behind the current critical path

**Why now:** Both are valuable, but neither should block the immediate remote P2 activation.

**Files:**
- Update later: `D:\GitHub\auto\V1升级方案.md`
- Future plan targets:
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-langfuse-tracing-rollout.md`
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-opencli-pilot.md`

- [ ] **Step 1: Treat Langfuse as observability work, not routing work**

Langfuse starts after P2-A remote validation is complete.

- [ ] **Step 2: Treat OpenCLI as a local-sidecar pilot**

OpenCLI should follow the same boundary now used for `lark-cli`:

```text
local helper first
no GitHub Actions dependency
no main collection-chain coupling
```

## Exit Criteria For “Ready To Continue”

This repo is ready to continue the project plan when all of the following are true:

- local Feishu sidecar remains local-only and GitHub Actions-safe
- local routing tests are green
- remote workflow env contract is validated with one manual run
- P1 tail is explicitly narrowed to real unresolved items
- next implementation batch is a single focused item, not “P2 everything at once”

## Recommended Immediate Next Batch

If work continues right away, the next batch should be:

1. **Remote P2-A validation on GitHub Actions**
2. **P1 tail confirmation (`anthropic-news` / RSSHub residuals)**
3. **Decision doc for discovery/search lead promotion**

Only after those three should the repo move into:

4. **P2-B LiteLLM Gateway**
5. **P2-C Langfuse tracing**
6. **P2.5 OpenCLI pilot**
