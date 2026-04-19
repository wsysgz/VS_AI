# Langfuse Tracing First Batch Design

> Workspace: `D:\GitHub\auto`
>
> Scope: add metadata-first Langfuse tracing to the main `run-once` pipeline without changing provider routing or uploading full prompt/response bodies by default.

## Goal

Give the repo a real trace surface for `run-once` so each run, stage, and LLM call can be observed and compared without turning tracing into a second project.

## Why now

- `run-status.json` already captures end-state metrics, but not the execution graph behind them.
- P2-B LiteLLM Gateway is now working with stage aliases, so the next engineering need is visibility into which stage used which route, how long it took, and where fallback happened.
- The repo already has stage timing and `ai_metrics`; Langfuse should complement these, not replace them.

## First-batch boundary

This batch includes:

1. optional Langfuse client initialization from env
2. one root trace per `run_once`
3. spans for `collection`, `dedup_score`, `rendering`, and `push_total`
4. generation observations for `prefilter`, `analysis`, `summary`, and `forecast`
5. `run-status.json` exposure of minimal tracing metadata

This batch does not include:

- prompt evaluator tracing
- discovery/search helper tracing
- Feishu sidecar tracing
- GitHub Actions rollout for Langfuse
- full prompt/response upload by default

## Metadata-first policy

Default behavior:

- upload metadata, timing, usage, provider, model, stage, and status
- do not upload prompt text or model output text

Optional later switch:

- `LANGFUSE_CAPTURE_CONTENT=true`

When disabled, observations still include:

- stage name
- provider / model
- token counts
- latency
- publication mode
- run risk level
- fallback status

## Trace shape

Root trace:

- name: `vs-ai-run-once`
- metadata: publication mode, reviewer, workspace, timezone

Pipeline spans:

- `collection`
- `dedup_score`
- `rendering`
- `push_total`

AI stage spans, nested under `dedup_score`:

- `prefilter`
- `analysis`
- `summary`
- `forecast`

Generation observations:

- created from `call_llm()`
- parented to the matching stage span when present
- otherwise parented to the root span

## File impact

- Create: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\ai_pipeline.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\run_once.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\requirements.txt`
- Modify: `D:\GitHub\auto\.env.example`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\用户操作手册.md`
- Test: `D:\GitHub\auto\tests\test_langfuse_tracing.py`
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`
- Test: `D:\GitHub\auto\tests\test_run_once.py`

## Success criteria

1. tracing is off by default and safe when Langfuse is absent or unconfigured
2. enabling tracing adds root trace + pipeline spans + LLM generations
3. stage alias runs preserve `provider=litellm_proxy`, with model values attached per generation
4. `run-status.json` includes a lightweight tracing block
5. no prompt/response text is uploaded unless explicitly enabled
