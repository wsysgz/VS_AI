# P2 AI Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repo’s stage routing reflect the intended model split: `summary`, `pre_filter`, and future helper stages use MiniMax-M2.7 by default, while `analysis` and `forecast` stay on DeepSeek.

**Architecture:** Reuse the existing stage-based routing mechanism in `llm_client.py`, but extend the settings/documentation contract and move `pre_filter` onto its own helper stage. Do not build a new discovery subsystem yet; only establish the stage contract and helper-stage readiness.

**Tech Stack:** Python, existing OpenAI-compatible LLM client, pytest, repo docs.

---

## File Map

- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\scoring_llm.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\V1升级方案.md`
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_scoring_llm.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`

### Task 1: Add helper-stage env coverage in settings and llm client

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`

- [ ] **Step 1: Write the failing tests**

Add tests that verify:

```python
config = _resolve_provider_config(stage="prefilter")
assert config["provider"] == "minimax_svips"

settings = load_settings(Path.cwd())
assert settings.env["PREFILTER_AI_PROVIDER"] == "minimax_svips"
assert settings.env["DISCOVERY_AI_MODEL"] == "MiniMax-M2.7"
assert settings.env["SEARCH_AI_MODEL"] == "MiniMax-M2.7"
```

- [ ] **Step 2: Run targeted tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_settings.py -q
```

Expected: FAIL because helper-stage env keys are not yet fully covered.

- [ ] **Step 3: Implement minimal helper-stage support**

In `D:\GitHub\auto\src\auto_report\settings.py`, add:

```python
"PREFILTER_AI_PROVIDER": os.environ.get("PREFILTER_AI_PROVIDER", ""),
"PREFILTER_AI_BASE_URL": os.environ.get("PREFILTER_AI_BASE_URL", ""),
"PREFILTER_AI_MODEL": os.environ.get("PREFILTER_AI_MODEL", ""),
"DISCOVERY_AI_PROVIDER": os.environ.get("DISCOVERY_AI_PROVIDER", ""),
"DISCOVERY_AI_BASE_URL": os.environ.get("DISCOVERY_AI_BASE_URL", ""),
"DISCOVERY_AI_MODEL": os.environ.get("DISCOVERY_AI_MODEL", ""),
"SEARCH_AI_PROVIDER": os.environ.get("SEARCH_AI_PROVIDER", ""),
"SEARCH_AI_BASE_URL": os.environ.get("SEARCH_AI_BASE_URL", ""),
"SEARCH_AI_MODEL": os.environ.get("SEARCH_AI_MODEL", ""),
```

In `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`, ensure helper stages participate in enablement checks where appropriate.

- [ ] **Step 4: Re-run targeted tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/llm_client.py src/auto_report/settings.py tests/test_llm_client.py tests/test_settings.py
git commit -m "feat: add helper stage ai routing contract"
```

### Task 2: Move pre-filter off analysis and onto MiniMax-owned stage

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\scoring_llm.py`
- Test: `D:\GitHub\auto\tests\test_scoring_llm.py`

- [ ] **Step 1: Write the failing test**

Change/add a test that requires:

```python
assert seen == ["prefilter"]
```

instead of `analysis`.

- [ ] **Step 2: Run the targeted test and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_scoring_llm.py -q
```

Expected: FAIL because `batch_score_candidates(...)` still routes through `analysis`.

- [ ] **Step 3: Implement the minimal routing change**

In `D:\GitHub\auto\src\auto_report\pipeline\scoring_llm.py`, change:

```python
raw = call_llm(prompt, stage="analysis")
```

to:

```python
raw = call_llm(prompt, stage="prefilter")
```

- [ ] **Step 4: Re-run the targeted test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_scoring_llm.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/pipeline/scoring_llm.py tests/test_scoring_llm.py
git commit -m "feat: route prefilter to its own ai stage"
```

### Task 3: Document the new division of labor

**Files:**
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\V1升级方案.md`

- [ ] **Step 1: Write the documentation checklist**

Docs must clearly state:

```text
analysis  -> DeepSeek
summary   -> MiniMax-M2.7
forecast  -> DeepSeek
prefilter -> MiniMax-M2.7
discovery -> MiniMax-M2.7
search    -> MiniMax-M2.7
```

- [ ] **Step 2: Verify docs are incomplete**

Run:

```powershell
rg -n "PREFILTER_AI_PROVIDER|DISCOVERY_AI_PROVIDER|SEARCH_AI_PROVIDER|MiniMax-M2.7" README.md AI对接手册.md V1升级方案.md
```

Expected: helper-stage contract is incomplete or absent.

- [ ] **Step 3: Add explicit routing guidance**

Update docs with:

- core report stage ownership
- helper-stage ownership
- reminder that OpenCLI pilot is future work and should use online research first

- [ ] **Step 4: Re-run the grep check**

Run:

```powershell
rg -n "PREFILTER_AI_PROVIDER|DISCOVERY_AI_PROVIDER|SEARCH_AI_PROVIDER|MiniMax-M2.7" README.md AI对接手册.md V1升级方案.md
```

Expected: docs now contain the helper-stage contract.

- [ ] **Step 5: Commit**

```bash
git add README.md AI对接手册.md V1升级方案.md
git commit -m "docs: define p2 ai stage ownership"
```

### Task 4: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run targeted routing tests**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_scoring_llm.py tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 2: Run adjacent stage tests**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_ai_pipeline.py tests/test_run_once.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full suite**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Commit verification checkpoint**

```bash
git status --short
git commit --allow-empty -m "chore: verify p2 ai routing"
```
