# Provider Fallback And Budget Guardrails Design

> Workspace: `D:\GitHub\auto`
>
> Scope: add provider fallback, budget guardrails, and per-stage latency/token budgets to the existing staged AI pipeline without changing the current pipeline fallback model.

## Goal

Make staged AI execution more controllable by giving each stage one extra provider retry path plus explicit latency/token guardrails, while preserving the existing non-AI fallback behavior already implemented in the pipeline.

## Why now

- `P2-A` stage routing is already verified, so the next weakness is what happens when a routed provider is slow, unavailable, or too expensive.
- `P2-C` tracing is now verified, so the repo can carry richer stage execution metadata without inventing a second observability path.
- The pipeline already has fallback behavior for `prefilter`, `analysis`, `summary`, and `forecast`; what is missing is a provider-level retry policy before falling back to non-AI output.

## Boundary

This design includes:

1. one backup-provider retry per stage
2. one latency guardrail per stage
3. one total-token guardrail per stage
4. `ai_metrics` exposure of backup usage and guardrail triggers
5. `run-status.json` compatibility through the existing `ai_metrics` payload

This design does not include:

- dashboard UI changes
- prompt-eval tracing work
- dynamic multi-step provider ranking
- monthly/daily spend accounting
- hard-stop whole-run cancellation when one stage exceeds budget

## Chosen behavior

Default stage behavior:

1. call the stage’s primary provider
2. if the request fails, or succeeds but exceeds a configured latency/token guardrail, retry the same stage once with the backup provider
3. if the backup provider also fails or exceeds the guardrail, raise an exception back to the pipeline
4. the existing pipeline layer continues to decide whether that stage becomes `ok` or `fallback`

This keeps two layers separate:

- provider fallback inside the LLM client
- pipeline fallback inside `ai_pipeline.py`

## Configuration model

Global backup provider:

- `BACKUP_AI_PROVIDER`
- `BACKUP_AI_BASE_URL`
- `BACKUP_AI_MODEL`
- `BACKUP_AI_API_KEY`

Stage-specific backup override:

- `ANALYSIS_BACKUP_AI_PROVIDER`
- `ANALYSIS_BACKUP_AI_BASE_URL`
- `ANALYSIS_BACKUP_AI_MODEL`
- `ANALYSIS_BACKUP_AI_API_KEY`

Apply the same pattern to:

- `SUMMARY_*`
- `FORECAST_*`
- `PREFILTER_*`
- `DISCOVERY_*`
- `SEARCH_*`

Global budget guardrails:

- `AI_MAX_STAGE_LATENCY_SECONDS`
- `AI_MAX_STAGE_TOTAL_TOKENS`

Stage-specific budget override:

- `ANALYSIS_AI_MAX_LATENCY_SECONDS`
- `ANALYSIS_AI_MAX_TOTAL_TOKENS`

Apply the same pattern to:

- `SUMMARY_*`
- `FORECAST_*`
- `PREFILTER_*`
- `DISCOVERY_*`
- `SEARCH_*`

## Metrics contract

Keep `stage_status` unchanged:

- `ok` means the stage produced AI output, even if backup provider was used
- `fallback` means the stage dropped to the existing non-AI fallback

Extend `ai_metrics` with:

- top level:
  - `backup_stages`
  - `guardrail_stages`
- per stage in `stage_breakdown[stage]`:
  - `attempts`
  - `backup_used`
  - `guardrail_triggered`
  - `guardrail_reason`
  - `primary_provider`
  - `primary_model`
  - `final_provider`
  - `final_model`
  - `budget`
    - `max_latency_seconds`
    - `max_total_tokens`

## Design choice

Three possible approaches were considered:

1. keep all logic inline in `llm_client.py`
2. add a small policy layer beside `llm_client.py`
3. terminate a stage immediately on guardrail exceedance without trying backup

The chosen design is a lightweight version of option 2:

- keep HTTP execution in `llm_client.py`
- add small helper functions for backup config resolution and guardrail evaluation
- do not create a heavyweight orchestration layer

This gives better separation than pure inline code without introducing a new subsystem.

## File impact

- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\tests\test_llm_client.py`
- Modify: `D:\GitHub\auto\tests\test_settings.py`
- Modify: `D:\GitHub\auto\tests\test_run_once.py`

## Success criteria

1. a stage can resolve a primary provider and an optional backup provider
2. request failure or guardrail exceedance triggers exactly one backup-provider retry
3. if backup also fails, the existing pipeline fallback remains the final safety net
4. `ai_metrics.stage_breakdown` records backup usage and guardrail metadata per stage
5. existing successful runs keep working when no backup/budget env is configured
