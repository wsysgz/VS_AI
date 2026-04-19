# Remote Provider Enable Checklist

> Workspace: `D:\GitHub\auto`
>
> Purpose: enable and safely validate remote GitHub Actions provider routing after the workflow rollout landed.

## 1. Repository Variables

### Keep current default DeepSeek mode

You can leave all of these unset if you want remote runs to keep using DeepSeek:

- `AI_PROVIDER`
- `AI_BASE_URL`
- `AI_MODEL`
- `ANALYSIS_AI_PROVIDER`
- `ANALYSIS_AI_BASE_URL`
- `ANALYSIS_AI_MODEL`
- `SUMMARY_AI_PROVIDER`
- `SUMMARY_AI_BASE_URL`
- `SUMMARY_AI_MODEL`
- `FORECAST_AI_PROVIDER`
- `FORECAST_AI_BASE_URL`
- `FORECAST_AI_MODEL`

### Recommended explicit default DeepSeek setup

If you want the remote contract to be explicit instead of relying on defaults, set:

```text
AI_PROVIDER=deepseek
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
```

### Recommended stage-level dual-provider setup

If you want `analysis=DeepSeek`, `summary=MiniMax`, `forecast=DeepSeek`, set:

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

PREFILTER_AI_PROVIDER=minimax_svips
PREFILTER_AI_BASE_URL=https://api.svips.org/v1
PREFILTER_AI_MODEL=MiniMax-M2.7

DISCOVERY_AI_PROVIDER=minimax_svips
DISCOVERY_AI_BASE_URL=https://api.svips.org/v1
DISCOVERY_AI_MODEL=MiniMax-M2.7

SEARCH_AI_PROVIDER=minimax_svips
SEARCH_AI_BASE_URL=https://api.svips.org/v1
SEARCH_AI_MODEL=MiniMax-M2.7
```

## 2. Repository Secrets

### Required for current DeepSeek-default path

- `DEEPSEEK_API_KEY`

### Required when using a non-DeepSeek global provider

- `AI_API_KEY`

### Optional for stage-level routing

Only add these when a stage truly needs its own secret instead of the global fallback:

- `ANALYSIS_AI_API_KEY`
- `SUMMARY_AI_API_KEY`
- `FORECAST_AI_API_KEY`
- `PREFILTER_AI_API_KEY`
- `DISCOVERY_AI_API_KEY`
- `SEARCH_AI_API_KEY`

## 3. Recommended enablement order

### Option A: safest first pass

Use this when you want to prove the workflow wiring works before changing providers.

1. Ensure `DEEPSEEK_API_KEY` exists
2. Leave all new provider variables unset
3. Run one manual remote validation with `push_enabled=false`
4. Confirm remote still behaves exactly like today's DeepSeek path

### Option B: switch remote default provider

Use this when you want the whole remote pipeline to use one OpenAI-compatible provider.

1. Set:
   - `AI_PROVIDER`
   - `AI_BASE_URL`
   - `AI_MODEL`
2. Add `AI_API_KEY`
3. Keep `DEEPSEEK_API_KEY` in place until the new path is proven stable
4. Run one manual remote validation with `push_enabled=false`

### Option C: enable stage-level routing

Use this after Option A or B is already stable.

1. Keep global fallback configured
2. Add only the specific stage variables you need:
   - `ANALYSIS_*`
   - `SUMMARY_*`
   - `FORECAST_*`
   - `PREFILTER_*`
   - `DISCOVERY_*`
   - `SEARCH_*`
3. Add stage-specific secrets only where required
4. Run one manual remote validation with `push_enabled=false`

## 4. First remote validation run

Open GitHub Actions and manually trigger `Collect And Report`.

Use:

- `push_enabled=false`
- `publication_mode=reviewed`
- `reviewer=codex`
- `review_note=remote provider validation`

## 5. What to check after the run

### GitHub Actions level

- `workflow-guard` passed
- `test` passed
- `collect` passed
- `analyze` passed
- `report` passed
- `deploy-pages` / `ops-dashboard` / `review-queue` passed

### Artifact / output level

Check the generated `run-status.json` in the workflow artifacts or pushed report outputs.

Confirm:

- `stage_status.analysis == "ok"`
- `stage_status.summary == "ok"`
- `stage_status.forecast == "ok"`
- `ai_metrics.provider` matches expectation
- `ai_metrics.model` matches expectation
- `ai_metrics.stage_breakdown.analysis.provider` matches expectation
- `ai_metrics.stage_breakdown.summary.provider` matches expectation
- `ai_metrics.stage_breakdown.forecast.provider` matches expectation
- `delivery_results.skipped_channels` contains all channels for the validation run

## 6. Expected interpretations

### If everything still shows DeepSeek

That is correct when:

- only `DEEPSEEK_API_KEY` is configured
- no new provider variables were added

### If only summary changes provider

That is correct when:

- global fallback remains DeepSeek
- only `SUMMARY_*` variables and matching key are configured

### If all stages fall back unexpectedly

Check in this order:

1. the workflow run used the latest pushed commit
2. the repository variable names exactly match the workflow names
3. the matching secret exists
4. the base URL has the correct `/v1` contract for OpenAI-compatible providers
5. `run-status.json` reflects the expected `ai_metrics.stage_breakdown`

## 7. Rollout recommendation

Recommended rollout path:

1. Keep remote default on DeepSeek
2. Run one manual validation with `push_enabled=false`
3. Enable only `SUMMARY_*` for MiniMax if you want a low-risk first split
4. Run another manual validation with `push_enabled=false`
5. Only after both runs look correct, decide whether to keep stage routing permanently
