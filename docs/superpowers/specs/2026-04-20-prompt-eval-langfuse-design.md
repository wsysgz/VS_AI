# Prompt Eval Langfuse Design

> Workspace: `D:\GitHub\auto`
>
> Scope: add Langfuse tracing to `evaluate-prompts` so offline prompt evaluation results share the same trace surface as the production `run-once` pipeline.

## Goal

Give prompt evaluation runs a real trace hierarchy so the repo can compare offline prompt scoring and production execution inside one observability system, without changing the existing JSON output contract or turning prompt eval into a separate tracing subsystem.

## Why now

- `P2-C` rollout is now verified for `run-once`, so the next natural P2 tail task is to unify offline and online trace dimensions.
- `evaluate-prompts` already writes structured results to `out/evals/*.json`, but there is no execution graph showing which case, prompt, version, and model produced each score bundle.
- The ops dashboard already reads recent prompt eval artifacts; adding Langfuse here should complement that artifact flow, not replace it.

## Boundary

This design includes:

1. one root trace per `evaluate-prompts` command
2. one span per dataset case
3. one generation observation per evaluated output
4. metadata-first capture for prompt eval, consistent with `run-once`
5. minimal adapter reuse so prompt eval tracing and `run-once` tracing share the same Langfuse integration path

This design does not include:

- prompt eval budget guardrails
- prompt eval result schema changes beyond optional tracing metadata
- dashboard UI changes
- automatic cross-linking between prompt eval traces and production traces
- source-governance or delivery-surface work

## Recommended shape

Root trace:

- name: `vs-ai-evaluate-prompts`
- metadata:
  - dataset path
  - case count
  - evaluation count
  - workspace
  - timezone

Case span:

- name: `prompt-eval-case:<case_id>`
- metadata:
  - `case_id`
  - `stage`
  - `output_count`

Generation observation:

- one per item in `outputs`
- name: `llm:prompt_eval`
- parented to the matching case span
- metadata:
  - `case_id`
  - `stage`
  - `prompt_id`
  - `version`
  - `model`
  - `tags`
  - score bundle fields from `metrics`

## Metadata-first policy

Default behavior:

- upload dataset path, stage, prompt id, version, model, tags, metric bundle, and aggregate counts
- do not upload reference text or candidate content when `LANGFUSE_CAPTURE_CONTENT=false`

Optional later switch:

- `LANGFUSE_CAPTURE_CONTENT=true`

When capture is disabled, prompt eval still remains useful because Langfuse will show:

- which cases were evaluated
- which prompt/version/model combinations were scored
- the resulting metric bundle for each output
- the aggregate run metadata

## File impact

- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\prompt_evaluator.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`
- Test: `D:\GitHub\auto\tests\test_prompt_evaluator.py`
- Test: `D:\GitHub\auto\tests\test_langfuse_tracing.py`

## Design choice

There are three realistic approaches:

1. root trace only
2. root trace + case spans + generation observations
3. no Langfuse integration, keep JSON-only eval output

The chosen design is option 2 because it matches the existing `run-once` tracing granularity closely enough to be operationally useful while still keeping the implementation small.

## Adapter change

The existing adapter already supports:

- root trace creation
- named spans
- generation observations

Prompt eval needs one small extension:

- `start_generation_trace(...)` should accept an optional `parent_name`

This allows prompt eval to:

- keep `stage="prompt_eval"` for all eval generations
- parent each generation under the case span instead of forcing case names into the stage field

This is the only intended adapter API change.

## Failure handling

- Langfuse remains optional; if it is disabled or unavailable, `evaluate-prompts` must still write its JSON artifact successfully.
- Prompt eval tracing must never fail the command on its own.
- If trace URL lookup fails, the command should still succeed and write the JSON result.
- Prompt eval should use the same metadata-first default as production tracing.

## Success criteria

1. `evaluate-prompts` writes the same JSON artifact as before
2. when Langfuse is configured, one root trace is created per command
3. each dataset case creates one span
4. each evaluated output creates one generation observation under the corresponding case span
5. `LANGFUSE_CAPTURE_CONTENT=false` prevents reference/candidate bodies from being uploaded
6. tracing errors do not break the prompt eval command
