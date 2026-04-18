# P2 AI Routing Design

> Workspace: `D:\GitHub\auto`
>
> Scope: move from a single effective AI path to explicit stage-based model ownership, with MiniMax-M2.7 taking `summary`, `pre_filter`, and future discovery/search helper work, while DeepSeek remains the default for `analysis` and `forecast`.

## Goal

Upgrade the repo from "stage routing exists in principle" to "stage routing is explicit, documented, testable, and extensible for source exploration work".

The target state is:

- `analysis` -> DeepSeek
- `summary` -> MiniMax-M2.7
- `forecast` -> DeepSeek
- `pre_filter` -> MiniMax-M2.7
- future `discovery` / `search` helper flows -> MiniMax-M2.7

## Why this boundary is right now

The repo already supports stage-specific environment overrides in `llm_client.py`, and `analysis`, `summary`, `forecast` are already wired through that path.

What is still missing is the next layer of maturity:

1. `pre_filter` still piggybacks on `analysis`
2. there is no first-class notion of governance/discovery helper stages
3. settings/docs/workflows do not yet describe the full routing contract for the next phase

This means the code has the primitive, but the product does not yet have a clean P2 operating model.

## Design summary

This batch should create one coherent AI-routing contract with two classes of stages.

### Class A: Core reporting stages

These directly affect the published report.

- `analysis`
- `summary`
- `forecast`

Default ownership:

- `analysis` -> DeepSeek
- `summary` -> MiniMax-M2.7
- `forecast` -> DeepSeek

### Class B: Helper / governance stages

These support source exploration and filtering, not direct report publication.

- `pre_filter`
- `discovery`
- `search`

Default ownership:

- `pre_filter` -> MiniMax-M2.7
- `discovery` -> MiniMax-M2.7
- `search` -> MiniMax-M2.7

## Routing contract

The routing contract should be explicit in code and docs, not hidden in convention.

Expected stage env contract:

- `ANALYSIS_AI_PROVIDER`
- `ANALYSIS_AI_BASE_URL`
- `ANALYSIS_AI_MODEL`
- `ANALYSIS_AI_API_KEY`

- `SUMMARY_AI_PROVIDER`
- `SUMMARY_AI_BASE_URL`
- `SUMMARY_AI_MODEL`
- `SUMMARY_AI_API_KEY`

- `FORECAST_AI_PROVIDER`
- `FORECAST_AI_BASE_URL`
- `FORECAST_AI_MODEL`
- `FORECAST_AI_API_KEY`

- `PREFILTER_AI_PROVIDER`
- `PREFILTER_AI_BASE_URL`
- `PREFILTER_AI_MODEL`
- `PREFILTER_AI_API_KEY`

- `DISCOVERY_AI_PROVIDER`
- `DISCOVERY_AI_BASE_URL`
- `DISCOVERY_AI_MODEL`
- `DISCOVERY_AI_API_KEY`

- `SEARCH_AI_PROVIDER`
- `SEARCH_AI_BASE_URL`
- `SEARCH_AI_MODEL`
- `SEARCH_AI_API_KEY`

Global fallback remains:

- `AI_PROVIDER`
- `AI_BASE_URL`
- `AI_MODEL`
- `AI_API_KEY`

## Core behavior changes

### 1. `pre_filter` must stop using `analysis`

Right now `scoring_llm.py` routes through `call_llm(..., stage="analysis")`.

That is correct for compatibility, but wrong for the intended P2 ownership model.

The batch should switch `pre_filter` to:

- `call_llm(..., stage="prefilter")`

This is the highest-value code change in the batch because it converts a conceptual ownership split into real runtime behavior.

### 2. Discovery/search should start as helper contract, not full pipeline

This batch should not build a giant new autonomous source discovery subsystem.

Instead, it should establish:

- stage names
- env support
- small helper entrypoints or helper functions
- optional artifact-oriented outputs

So later source exploration work can plug into the same routing scheme without refactoring `llm_client.py` again.

### 3. Metrics must remain stage-aware

The current `llm_client.py` already records `stage_breakdown`.

This batch should preserve and extend that:

- `prefilter` shows separately from `analysis`
- future helper stages can appear naturally in metrics without additional schema redesign

## File impact

### Core routing

- `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
  - no major redesign required
  - confirm helper stages resolve correctly
  - extend `is_llm_enabled()` to include helper stages if needed

### Filtering path

- `D:\GitHub\auto\src\auto_report\pipeline\scoring_llm.py`
  - change from `analysis` stage to `prefilter`

### Settings snapshot

- `D:\GitHub\auto\src\auto_report\settings.py`
  - include `PREFILTER_*`
  - include `DISCOVERY_*`
  - include `SEARCH_*`

### Tests

- `D:\GitHub\auto\tests\test_llm_client.py`
  - helper-stage config resolution
  - helper-stage metrics visibility
- `D:\GitHub\auto\tests\test_scoring_llm.py`
  - assert `prefilter` stage is used
- `D:\GitHub\auto\tests\test_settings.py`
  - helper-stage env exposure

### Docs

- `D:\GitHub\auto\README.md`
- `D:\GitHub\auto\AI对接手册.md`
- `D:\GitHub\auto\V1升级方案.md`
- optional helper note:
  - `D:\GitHub\auto\docs\superpowers\plans\2026-04-18-remote-provider-enable-checklist.md`

## Explicit defaults

This batch should document these recommended defaults:

```text
ANALYSIS_*  -> DeepSeek
SUMMARY_*   -> MiniMax-M2.7
FORECAST_*  -> DeepSeek
PREFILTER_* -> MiniMax-M2.7
DISCOVERY_* -> MiniMax-M2.7
SEARCH_*    -> MiniMax-M2.7
```

The actual repo should still behave safely when only global values are configured.

## Discovery/search scope guard

This batch should **not**:

- crawl the open web automatically
- replace current source governance logic
- add a browser automation dependency
- introduce OpenCLI runtime into the main collection chain

But it should leave the helper-stage contract ready for those later uses.

## OpenCLI pilot note

OpenCLI should remain a future pilot, not part of this implementation batch.

However, when that pilot starts, it should be informed by real external research:

- official docs
- official examples
- issue/discussion failure modes
- login/session behavior
- deterministic CLI behavior under repeated runs

That research requirement should be documented now so later implementation does not treat OpenCLI as a drop-in shortcut.

## Verification strategy

Minimum verification for this batch:

1. `tests/test_llm_client.py`
2. `tests/test_scoring_llm.py`
3. `tests/test_settings.py`
4. targeted `run_once` / `ai_pipeline` tests if any stage expectations change
5. full `python -m pytest tests -q`

## Success criteria

This P2 batch is successful when:

1. `summary` is explicitly documented as MiniMax-owned
2. `pre_filter` no longer routes through `analysis`
3. helper-stage env keys exist for `prefilter`, `discovery`, and `search`
4. tests prove helper-stage resolution works
5. repo docs describe the new AI division of labor clearly
