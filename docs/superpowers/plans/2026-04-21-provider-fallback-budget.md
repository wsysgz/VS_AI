# Provider Fallback And Budget Guardrails Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one backup-provider retry plus per-stage latency/token guardrails to the staged AI client while preserving the current pipeline fallback behavior.

**Architecture:** Extend `llm_client.py` with helper-based policy resolution instead of creating a separate orchestration service. The LLM client will resolve primary and backup configs, evaluate latency/token guardrails after each response, retry once on the backup provider, and record richer per-stage metrics. The pipeline layer keeps ownership of non-AI fallback decisions.

**Tech Stack:** Python, requests, existing staged AI pipeline, pytest.

---

## File Map

- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\tests\test_llm_client.py`
- Modify: `D:\GitHub\auto\tests\test_settings.py`
- Modify: `D:\GitHub\auto\tests\test_run_once.py`

### Task 1: Add failing config-resolution tests for backup providers and budgets

**Files:**
- Modify: `D:\GitHub\auto\tests\test_llm_client.py`
- Modify: `D:\GitHub\auto\tests\test_settings.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`

- [ ] **Step 1: Add failing tests for backup provider resolution**

Add tests that prove:

```python
def test_stage_specific_backup_provider_resolution():
    ...

def test_global_backup_provider_resolution():
    ...
```

They should expect `summary` or `analysis` to resolve `BACKUP_*` / `SUMMARY_BACKUP_*` env values separately from the primary provider.

- [ ] **Step 2: Add failing tests for per-stage budget resolution**

Add tests that prove:

```python
def test_stage_specific_budget_resolution():
    ...

def test_global_budget_resolution():
    ...
```

They should expect latency/token limits to resolve from `ANALYSIS_AI_MAX_LATENCY_SECONDS`, `ANALYSIS_AI_MAX_TOTAL_TOKENS`, or the global equivalents.

- [ ] **Step 3: Run the new config tests red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py -q
python -m pytest tests/test_settings.py -q
```

Expected: FAIL because backup/budget resolution does not exist yet.

- [ ] **Step 4: Implement minimal config-resolution helpers**

Add helper functions in `D:\GitHub\auto\src\auto_report\integrations\llm_client.py` and env exposure in `D:\GitHub\auto\src\auto_report\settings.py` for:

```python
_resolve_backup_provider_config(stage)
_resolve_stage_budget(stage)
```

The budget helper should return parsed numeric limits or `None` when unset.

- [ ] **Step 5: Re-run the config tests green**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py -q
python -m pytest tests/test_settings.py -q
```

Expected: PASS for the new config-resolution cases.

### Task 2: Add failing client tests for backup retry and guardrail triggers

**Files:**
- Modify: `D:\GitHub\auto\tests\test_llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`

- [ ] **Step 1: Add a failing test for primary failure -> backup retry -> success**

Add a test shaped like:

```python
@patch("auto_report.integrations.llm_client._session")
def test_stage_uses_backup_provider_after_primary_failure(mock_session):
    ...
```

It should assert:
- first call targets primary endpoint
- second call targets backup endpoint
- final result succeeds
- metrics show `backup_used=True`, `attempts=2`

- [ ] **Step 2: Add a failing test for latency/token guardrail -> backup retry**

Add tests shaped like:

```python
@patch("auto_report.integrations.llm_client._session")
def test_stage_uses_backup_provider_after_latency_guardrail(mock_session):
    ...

@patch("auto_report.integrations.llm_client._session")
def test_stage_uses_backup_provider_after_token_guardrail(mock_session):
    ...
```

They should simulate a successful primary response whose usage or measured latency exceeds the configured limit, then assert backup retry occurs.

- [ ] **Step 3: Add a failing test for backup failure -> caller gets exception**

Add:

```python
@patch("auto_report.integrations.llm_client._session")
def test_stage_raises_after_primary_and_backup_fail(mock_session):
    ...
```

It should prove the client stops after one backup retry and raises back to the pipeline.

- [ ] **Step 4: Run the new client tests red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py -q
```

Expected: FAIL because retry-on-backup and guardrail logic do not exist yet.

- [ ] **Step 5: Implement the minimal fallback + guardrail path in `call_llm()`**

Refactor `call_llm()` so it:
- resolves primary config
- resolves backup config once per stage
- executes primary request
- records metrics/guardrail state
- retries exactly once on backup when:
  - request failure occurs, or
  - latency exceeds configured limit, or
  - total tokens exceed configured limit

Do not change the existing outer pipeline fallback behavior.

- [ ] **Step 6: Re-run `tests/test_llm_client.py` green**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py -q
```

Expected: PASS.

### Task 3: Expose richer `ai_metrics` state to run-status tests

**Files:**
- Modify: `D:\GitHub\auto\tests\test_run_once.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`

- [ ] **Step 1: Add a failing run-status test for backup and guardrail fields**

Add a test shaped like:

```python
def test_build_run_status_preserves_backup_and_guardrail_ai_metrics():
    ...
```

It should assert `ai_metrics.stage_breakdown[stage]` keeps:
- `attempts`
- `backup_used`
- `guardrail_triggered`
- `guardrail_reason`
- `budget`

- [ ] **Step 2: Run the run-status test red**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_run_once.py -q
```

Expected: FAIL because the richer fields are not yet emitted or normalized consistently.

- [ ] **Step 3: Normalize `get_llm_metrics()` output to include the new fields**

Update `D:\GitHub\auto\src\auto_report\integrations\llm_client.py` so `get_llm_metrics()` returns:

```python
"backup_stages": [...],
"guardrail_stages": [...],
"stage_breakdown": {
    stage: {
        ...
        "attempts": ...,
        "backup_used": ...,
        "guardrail_triggered": ...,
        "guardrail_reason": ...,
        "primary_provider": ...,
        "primary_model": ...,
        "final_provider": ...,
        "final_model": ...,
        "budget": {
            "max_latency_seconds": ...,
            "max_total_tokens": ...,
        },
    }
}
```

- [ ] **Step 4: Re-run the run-status tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_run_once.py -q
```

Expected: PASS.

### Task 4: Run focused and full verification

**Files:**
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`
- Test: `D:\GitHub\auto\tests\test_run_once.py`

- [ ] **Step 1: Run focused verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_settings.py tests/test_run_once.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the full suite**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 3: Check the diff stays surgical**

Run:

```powershell
git diff --stat
```

Expected: only the planned runtime/test files changed for this feature slice.

- [ ] **Step 4: Commit the implementation**

Run:

```powershell
git add src/auto_report/integrations/llm_client.py src/auto_report/settings.py tests/test_llm_client.py tests/test_settings.py tests/test_run_once.py
git commit -m "feat: add ai fallback and budget guardrails"
```

Expected: one focused feature commit.
