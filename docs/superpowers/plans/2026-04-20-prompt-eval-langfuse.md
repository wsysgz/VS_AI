# Prompt Eval Langfuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Langfuse tracing to `evaluate-prompts` with one root trace per command, one span per case, and one generation per output while keeping the existing JSON artifact behavior unchanged.

**Architecture:** Reuse the existing `langfuse_tracing` adapter instead of creating a second tracing path. Extend the adapter minimally so generations can be parented under case spans, then have `cmd_evaluate_prompts` load settings and pass the env into `prompt_evaluator`, which owns the root trace, case spans, and prompt-output generations.

**Tech Stack:** Python, Langfuse Python SDK, pytest, existing `auto_report` CLI and tracing adapter.

---

## File Map

- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\prompt_evaluator.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`
- Test: `D:\GitHub\auto\tests\test_prompt_evaluator.py`
- Test: `D:\GitHub\auto\tests\test_langfuse_tracing.py`

### Task 1: Add failing adapter tests for case-parented generations

**Files:**
- Modify: `D:\GitHub\auto\tests\test_langfuse_tracing.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`

- [ ] **Step 1: Add a failing test for keyword-only parent selection**

Add this test after the existing trace-url tests:

```python
def test_start_generation_trace_can_parent_under_named_span(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
        name="vs-ai-evaluate-prompts",
        metadata={"dataset_path": "dataset.json"},
    )

    assert trace_state["enabled"] is True
    start_stage_span("prompt-eval-case:summary-case", metadata={"case_id": "summary-case"})

    observation = start_generation_trace(
        stage="prompt_eval",
        parent_name="prompt-eval-case:summary-case",
        provider="offline_eval",
        model="offline-dataset",
        input_payload={"content": {"one_line_core": "secret"}},
        metadata={"case_id": "summary-case", "prompt_id": "summary-v2"},
    )

    assert observation is not None
    assert fake_client.observations[-1].trace_context["parent_span_id"] == "obs-2"
    assert fake_client.observations[-1].name == "llm:prompt_eval"
```

- [ ] **Step 2: Run the new test and verify it fails for the expected reason**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_langfuse_tracing.py::test_start_generation_trace_can_parent_under_named_span -q
```

Expected: FAIL because `start_generation_trace()` does not accept `parent_name` yet.

- [ ] **Step 3: Implement the minimal adapter change**

Update the function signature and parenting call in `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`:

```python
def start_generation_trace(
    *,
    stage: str | None,
    parent_name: str | None = None,
    provider: str,
    model: str,
    input_payload: Any | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trace_state = get_active_trace_state()
    if not trace_state or not trace_state.get("enabled"):
        return None

    capture_content = bool(trace_state.get("capture_content", False))
    generation_metadata = {
        "stage": stage or "default",
        "provider": provider,
        "model": model,
        **(metadata or {}),
    }

    parent_key = parent_name if parent_name is not None else stage

    try:
        observation = trace_state["client"].start_observation(
            trace_context={
                "trace_id": trace_state["trace_id"],
                "parent_span_id": _parent_span_id(trace_state, parent_key),
            },
            name=f"llm:{stage or 'default'}",
            as_type="generation",
            model=model,
            input=sanitize_llm_content(input_payload, capture_content),
            metadata=generation_metadata,
        )
        return {
            "observation": observation,
            "observation_id": getattr(observation, "id", ""),
            "trace_id": getattr(observation, "trace_id", ""),
            "capture_content": capture_content,
        }
    except Exception:
        return None
```

- [ ] **Step 4: Re-run the adapter tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_langfuse_tracing.py -q
```

Expected: PASS.

### Task 2: Add failing prompt-evaluator tests for root trace, case spans, and output generations

**Files:**
- Modify: `D:\GitHub\auto\tests\test_prompt_evaluator.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\prompt_evaluator.py`

- [ ] **Step 1: Add a failing test that proves prompt eval emits the expected trace hierarchy**

Append this test to `D:\GitHub\auto\tests\test_prompt_evaluator.py`:

```python
def test_evaluate_prompt_dataset_emits_langfuse_root_case_and_generation_traces(tmp_path: Path, monkeypatch):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "summary-case",
                        "stage": "summary",
                        "reference": {
                            "one_line_core": "Evaluation becomes core",
                            "executive_summary": ["A", "B"],
                            "key_points": [{"title": "Signal", "why_it_matters": "Matters"}],
                            "key_insights": ["Insight"],
                            "limitations": ["Need verification"],
                            "actions": ["Track"],
                        },
                        "outputs": [
                            {
                                "prompt_id": "summary-v2",
                                "version": "v2",
                                "model": "offline-dataset",
                                "content": {
                                    "one_line_core": "Evaluation becomes core",
                                    "executive_summary": ["A", "B"],
                                    "key_points": [{"title": "Signal", "why_it_matters": "Matters"}],
                                    "key_insights": ["Insight"],
                                    "limitations": ["Need verification"],
                                    "actions": ["Track"],
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    trace_calls = {"root": [], "spans": [], "gens": [], "finishes": [], "flushes": 0}

    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_run_trace",
        lambda env, *, name, metadata: trace_calls["root"].append(
            {"env": env, "name": name, "metadata": metadata}
        ) or {
            "enabled": True,
            "trace_id": "trace-123",
            "trace_url": "https://langfuse.example/trace/trace-123",
        },
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_stage_span",
        lambda name, parent_name=None, metadata=None: trace_calls["spans"].append(
            {"name": name, "parent_name": parent_name, "metadata": metadata}
        ) or {"observation_id": name, "trace_id": "trace-123"},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_stage_span",
        lambda name, metadata=None, error=None: trace_calls["finishes"].append(
            {"name": name, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_generation_trace",
        lambda **kwargs: trace_calls["gens"].append(kwargs) or {"observation": object(), "capture_content": False},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_generation_trace",
        lambda trace_observation, output_text=None, metadata=None, usage_details=None, error=None: None,
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.complete_run_trace",
        lambda trace_state, metadata=None, error=None: trace_calls["root"].append(
            {"completed": True, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.flush_langfuse",
        lambda env=None: trace_calls.__setitem__("flushes", trace_calls["flushes"] + 1),
    )

    output_path = evaluate_prompt_dataset(
        tmp_path,
        dataset_path,
        env={
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 1
    assert trace_calls["root"][0]["name"] == "vs-ai-evaluate-prompts"
    assert trace_calls["spans"][0]["name"] == "prompt-eval-case:summary-case"
    assert trace_calls["gens"][0]["stage"] == "prompt_eval"
    assert trace_calls["gens"][0]["parent_name"] == "prompt-eval-case:summary-case"
    assert trace_calls["gens"][0]["provider"] == "offline_eval"
    assert trace_calls["flushes"] == 1
```

- [ ] **Step 2: Run the new prompt-evaluator test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_prompt_evaluator.py::test_evaluate_prompt_dataset_emits_langfuse_root_case_and_generation_traces -q
```

Expected: FAIL because `evaluate_prompt_dataset()` does not accept `env` and does not call tracing helpers yet.

- [ ] **Step 3: Add the prompt-eval tracing imports and env-aware signature**

Add these imports near the top of `D:\GitHub\auto\src\auto_report\pipeline\prompt_evaluator.py`:

```python
from typing import Mapping

from auto_report.integrations.langfuse_tracing import (
    complete_run_trace,
    finish_generation_trace,
    finish_stage_span,
    flush_langfuse,
    start_generation_trace,
    start_run_trace,
    start_stage_span,
)
```

Change the function signature to:

```python
def evaluate_prompt_dataset(
    root_dir: Path,
    dataset_path: Path,
    env: Mapping[str, str] | None = None,
) -> Path:
```

- [ ] **Step 4: Wrap the prompt-eval loop in one root trace and per-case spans**

Add this structure around the existing loop in `D:\GitHub\auto\src\auto_report\pipeline\prompt_evaluator.py`:

```python
    trace_state = start_run_trace(
        env,
        name="vs-ai-evaluate-prompts",
        metadata={
            "dataset_path": str(dataset_path),
            "workspace": str(root_dir),
        },
    )

    try:
        for raw_case in cases:
            stage = str(raw_case.get("stage", "")).strip()
            case_id = str(raw_case.get("id", "")).strip() or f"{stage}-case"
            outputs = raw_case.get("outputs", [])
            span_name = f"prompt-eval-case:{case_id}"

            start_stage_span(
                span_name,
                metadata={
                    "case_id": case_id,
                    "stage": stage,
                    "output_count": len(outputs) if isinstance(outputs, list) else 0,
                },
            )

            try:
                ...
            finally:
                finish_stage_span(
                    span_name,
                    metadata={
                        "case_id": case_id,
                        "stage": stage,
                        "evaluation_count": len(evaluations),
                    },
                )
    finally:
        complete_run_trace(
            trace_state,
            metadata={
                "dataset_path": str(dataset_path),
                "case_count": len(case_results),
                "evaluation_count": sum(len(case["evaluations"]) for case in case_results),
            },
        )
        flush_langfuse(env)
```

- [ ] **Step 5: Create one generation per output**

Inside the output loop, wrap each evaluation with `start_generation_trace` and `finish_generation_trace`:

```python
            generation_trace = start_generation_trace(
                stage="prompt_eval",
                parent_name=span_name,
                provider="offline_eval",
                model=model,
                input_payload={
                    "reference": reference if isinstance(reference, dict) else {},
                    "candidate": raw_output.get("content"),
                },
                metadata={
                    "case_id": case_id,
                    "stage": stage,
                    "prompt_id": prompt_id,
                    "version": version,
                    "model": model,
                    "tags": prompt_meta.get("tags", []),
                },
            )

            metrics = _metric_bundle(stage, reference if isinstance(reference, dict) else {}, raw_output.get("content"))

            finish_generation_trace(
                generation_trace,
                output_text=json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                metadata={
                    "case_id": case_id,
                    "stage": stage,
                    "prompt_id": prompt_id,
                    "version": version,
                    "model": model,
                    "tags": prompt_meta.get("tags", []),
                    **metrics,
                },
            )
```

- [ ] **Step 6: Re-run the prompt-evaluator tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_prompt_evaluator.py -q
```

Expected: PASS.

### Task 3: Pass real env from the CLI entrypoint

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\tests\test_prompt_evaluator.py`

- [ ] **Step 1: Add a failing app-level test proving `cmd_evaluate_prompts` forwards settings env**

Append this test to `D:\GitHub\auto\tests\test_prompt_evaluator.py`:

```python
def test_cmd_evaluate_prompts_passes_loaded_env(tmp_path: Path, monkeypatch):
    from auto_report.app import cmd_evaluate_prompts

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"cases": []}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "auto_report.app.load_settings",
        lambda root_dir: type("Settings", (), {"env": {"LANGFUSE_ENABLED": "true", "AUTO_TIMEZONE": "Asia/Shanghai"}})(),
    )

    captured = {}

    def _fake_eval(root_dir, resolved_dataset_path, env=None):
        captured["root_dir"] = root_dir
        captured["dataset_path"] = resolved_dataset_path
        captured["env"] = env
        return tmp_path / "out.json"

    monkeypatch.setattr("auto_report.pipeline.prompt_evaluator.evaluate_prompt_dataset", _fake_eval)

    result = cmd_evaluate_prompts(tmp_path, str(dataset_path))

    assert result == tmp_path / "out.json"
    assert captured["dataset_path"] == dataset_path
    assert captured["env"]["LANGFUSE_ENABLED"] == "true"
```

- [ ] **Step 2: Run the new app-level test and verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_prompt_evaluator.py::test_cmd_evaluate_prompts_passes_loaded_env -q
```

Expected: FAIL because `cmd_evaluate_prompts()` does not call `load_settings()` or pass `env`.

- [ ] **Step 3: Update `cmd_evaluate_prompts()` to pass the loaded env**

Change `D:\GitHub\auto\src\auto_report\app.py` to:

```python
def cmd_evaluate_prompts(root_dir: Path, dataset_path: str) -> Path:
    from auto_report.pipeline.prompt_evaluator import evaluate_prompt_dataset

    settings = load_settings(root_dir)
    return evaluate_prompt_dataset(root_dir, Path(dataset_path), env=settings.env)
```

- [ ] **Step 4: Re-run the prompt-evaluator test module**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_prompt_evaluator.py -q
```

Expected: PASS.

### Task 4: Run the focused regression set and the full test suite

**Files:**
- Test: `D:\GitHub\auto\tests\test_langfuse_tracing.py`
- Test: `D:\GitHub\auto\tests\test_prompt_evaluator.py`

- [ ] **Step 1: Run the focused regression set**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_langfuse_tracing.py tests/test_prompt_evaluator.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the full suite**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS with no new failures.

- [ ] **Step 3: Check the diff stays surgical**

Run:

```powershell
git diff --stat
```

Expected: only `app.py`, `prompt_evaluator.py`, `langfuse_tracing.py`, and the two test files changed.

- [ ] **Step 4: Commit the prompt-eval tracing slice**

Run:

```powershell
git add src/auto_report/app.py src/auto_report/pipeline/prompt_evaluator.py src/auto_report/integrations/langfuse_tracing.py tests/test_prompt_evaluator.py tests/test_langfuse_tracing.py
git commit -m "feat: trace prompt evaluation runs in langfuse"
```

Expected: one focused commit for the prompt-eval tracing feature.
