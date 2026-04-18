# GitHub Actions Provider Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make remote GitHub Actions runs consume the same configurable AI provider model as local stage-routing runs, without regressing the current DeepSeek-default path.

**Architecture:** Keep the current collect -> analyze -> report workflow chain and change only workflow/env wiring. Reusable workflows should accept unified AI env/secrets, default to today's DeepSeek behavior, and allow stage-specific overrides for analysis/summary/forecast when repository variables and secrets are present.

**Tech Stack:** GitHub Actions YAML, Python settings/env loading, pytest, PowerShell verification commands.

---

## File Map

- Modify: `D:\GitHubuto\.github\workflows\collect-report.yml`
- Modify: `D:\GitHubuto\.github\workflowseusable-analyze.yml`
- Modify: `D:\GitHubuto\.github\workflowseusable-report.yml`
- Modify: `D:\GitHubuto\.github\workflows\compensate-report.yml`
- Modify: `D:\GitHubuto\srcuto_report\settings.py`
- Modify: `D:\GitHubuto\README.md`
- Modify: `D:\GitHubuto\AI对接手册.md`
- Modify: `D:\GitHubuto\V1升级方案.md`
- Test: `D:\GitHubuto	ests	est_settings.py`
- Verify: `D:\GitHubuto\scripts\check-workflows.ps1`

### Task 1: Expose unified AI workflow inputs and defaults

**Files:**
- Modify: `D:\GitHubuto\.github\workflowseusable-analyze.yml`
- Modify: `D:\GitHubuto\.github\workflowseusable-report.yml`
- Modify: `D:\GitHubuto\.github\workflows\compensate-report.yml`
- Modify: `D:\GitHubuto\.github\workflows\collect-report.yml`

- [ ] **Step 1: Write the failing workflow expectation test/check**

Record the exact expected env contract in the plan before editing:

```text
Expected remote env contract:
- AI_PROVIDER / AI_BASE_URL / AI_MODEL / AI_API_KEY supported
- ANALYSIS_AI_PROVIDER / ANALYSIS_AI_BASE_URL / ANALYSIS_AI_MODEL / ANALYSIS_AI_API_KEY supported
- SUMMARY_AI_PROVIDER / SUMMARY_AI_BASE_URL / SUMMARY_AI_MODEL / SUMMARY_AI_API_KEY supported
- FORECAST_AI_PROVIDER / FORECAST_AI_BASE_URL / FORECAST_AI_MODEL / FORECAST_AI_API_KEY supported
- If no unified values are set, workflow keeps DeepSeek defaults
```

- [ ] **Step 2: Run workflow validation to confirm current gap**

Run:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
```

Expected: current workflow validation passes, but manual inspection still shows `reusable-analyze.yml` and `reusable-report.yml` hard-code `DEEPSEEK_API_KEY` and `AI_MODEL=deepseek-chat`.

- [ ] **Step 3: Make minimal workflow wiring change**

Update reusable workflow env blocks from the current hard-coded style:

```yaml
env:
  DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
  AI_MODEL: deepseek-chat
```

To a unified default-preserving style:

```yaml
env:
  AI_PROVIDER: ${{ vars.AI_PROVIDER || 'deepseek' }}
  AI_BASE_URL: ${{ vars.AI_BASE_URL || 'https://api.deepseek.com' }}
  AI_MODEL: ${{ vars.AI_MODEL || 'deepseek-chat' }}
  AI_API_KEY: ${{ secrets.AI_API_KEY }}
  DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
  ANALYSIS_AI_PROVIDER: ${{ vars.ANALYSIS_AI_PROVIDER }}
  ANALYSIS_AI_BASE_URL: ${{ vars.ANALYSIS_AI_BASE_URL }}
  ANALYSIS_AI_MODEL: ${{ vars.ANALYSIS_AI_MODEL }}
  ANALYSIS_AI_API_KEY: ${{ secrets.ANALYSIS_AI_API_KEY }}
```

Mirror the same pattern for `SUMMARY_*` and `FORECAST_*`, and keep fallback-safe defaults so existing DeepSeek-only repos continue to work.

- [ ] **Step 4: Re-run workflow validation**

Run:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
```

Expected: PASS for all workflow profiles.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/collect-report.yml .github/workflows/reusable-analyze.yml .github/workflows/reusable-report.yml .github/workflows/compensate-report.yml
git commit -m "feat: wire unified AI provider env into workflows"
```

### Task 2: Make settings snapshot include stage-level provider state

**Files:**
- Modify: `D:\GitHubuto\srcuto_report\settings.py`
- Test: `D:\GitHubuto	ests	est_settings.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.settings import load_settings


def test_load_settings_includes_stage_level_ai_env(monkeypatch, tmp_path):
    monkeypatch.setenv("ANALYSIS_AI_PROVIDER", "deepseek")
    monkeypatch.setenv("SUMMARY_AI_PROVIDER", "minimax_svips")
    monkeypatch.setenv("FORECAST_AI_MODEL", "deepseek-chat")
    settings = load_settings(tmp_path)
    assert settings.env["ANALYSIS_AI_PROVIDER"] == "deepseek"
    assert settings.env["SUMMARY_AI_PROVIDER"] == "minimax_svips"
    assert settings.env["FORECAST_AI_MODEL"] == "deepseek-chat"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_settings.py -q
```

Expected: FAIL because stage-level env keys are not yet included in `settings.env`.

- [ ] **Step 3: Write minimal implementation**

Extend the `env` dict in `D:\GitHubuto\srcuto_report\settings.py` with the exact stage keys used by the workflows and `llm_client.py`:

```python
"ANALYSIS_AI_PROVIDER": os.environ.get("ANALYSIS_AI_PROVIDER", ""),
"ANALYSIS_AI_BASE_URL": os.environ.get("ANALYSIS_AI_BASE_URL", ""),
"ANALYSIS_AI_MODEL": os.environ.get("ANALYSIS_AI_MODEL", ""),
"SUMMARY_AI_PROVIDER": os.environ.get("SUMMARY_AI_PROVIDER", ""),
"SUMMARY_AI_BASE_URL": os.environ.get("SUMMARY_AI_BASE_URL", ""),
"SUMMARY_AI_MODEL": os.environ.get("SUMMARY_AI_MODEL", ""),
"FORECAST_AI_PROVIDER": os.environ.get("FORECAST_AI_PROVIDER", ""),
"FORECAST_AI_BASE_URL": os.environ.get("FORECAST_AI_BASE_URL", ""),
"FORECAST_AI_MODEL": os.environ.get("FORECAST_AI_MODEL", ""),
```

Add matching `*_AI_API_KEY` snapshots only if they are already intentionally surfaced elsewhere; otherwise keep secret handling limited to runtime env.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/settings.py tests/test_settings.py
git commit -m "test: cover stage-level AI env settings"
```

### Task 3: Update operator docs for remote provider routing

**Files:**
- Modify: `D:\GitHubuto\README.md`
- Modify: `D:\GitHubuto\AI对接手册.md`
- Modify: `D:\GitHubuto\V1升级方案.md`

- [ ] **Step 1: Write the failing documentation checklist**

```text
Docs must answer:
1. Which GitHub Secrets are required for unified provider mode?
2. Which Repository Variables control global provider routing?
3. How to enable stage-specific routing remotely?
4. What happens when only DeepSeek secrets are configured?
```

- [ ] **Step 2: Verify current docs are incomplete**

Run:

```powershell
rg -n "ANALYSIS_AI_PROVIDER|SUMMARY_AI_PROVIDER|FORECAST_AI_PROVIDER|AI_API_KEY" README.md AI对接手册.md V1升级方案.md
```

Expected: incomplete or outdated remote workflow guidance.

- [ ] **Step 3: Update docs with exact remote contract**

Add a concise operator block like:

```env
AI_PROVIDER=deepseek
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
AI_API_KEY=<optional-openai-compatible-key>

ANALYSIS_AI_PROVIDER=deepseek
SUMMARY_AI_PROVIDER=minimax_svips
FORECAST_AI_PROVIDER=deepseek
```

Document that remote runs still default to DeepSeek until repository variables/secrets are explicitly set.

- [ ] **Step 4: Verify docs mention the new contract**

Run:

```powershell
rg -n "ANALYSIS_AI_PROVIDER|SUMMARY_AI_PROVIDER|FORECAST_AI_PROVIDER|AI_API_KEY" README.md AI对接手册.md V1升级方案.md
```

Expected: all three documents contain the updated remote-routing guidance.

- [ ] **Step 5: Commit**

```bash
git add README.md AI对接手册.md V1升级方案.md
git commit -m "docs: document remote stage-level AI routing"
```

### Task 4: Final verification and release checkpoint

**Files:**
- Verify only

- [ ] **Step 1: Run targeted Python verification**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_llm_client.py tests/test_settings.py tests/test_run_once.py -q
```

Expected: PASS.

- [ ] **Step 2: Run workflow verification**

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Manual remote readiness checklist**

```text
- Repository Secret DEEPSEEK_API_KEY still present
- Optional Repository Secret AI_API_KEY configured for OpenAI-compatible non-DeepSeek provider
- Optional stage-specific secrets configured only when truly needed
- Repository Variables match intended default provider
- Manual workflow_dispatch uses push_enabled=false for first remote validation
```

- [ ] **Step 5: Commit / tag release checkpoint**

```bash
git status --short
git commit --allow-empty -m "chore: mark provider rollout verification checkpoint"
```
