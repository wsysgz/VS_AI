# DeepSeek V4 And P3-B First-Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the repo's default DeepSeek model routing to V4 (`flash` for routine stages, `pro` for key stages including `summary`) and make the Feishu ops desk migrate existing tables to Chinese-first, writable-field-first layouts.

**Architecture:** Keep the current stage-routing contract and only swap default model names plus stage overrides. For Feishu ops desk, reuse the existing sidecar sync path so rerunning `sync-feishu-ops-desk` upgrades existing tables/views instead of introducing a one-off migration tool.

**Tech Stack:** Python, YAML config, existing GitHub workflow env contract, existing `lark-cli` sidecar integration, pytest

---

## File Structure

- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
  - update default DeepSeek model names
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
  - keep provider compatibility while defaulting to V4 names
- Modify: `D:\GitHub\auto\.github\workflows\reusable-analyze.yml`
  - update default remote model names
- Modify: `D:\GitHub\auto\.github\workflows\reusable-report.yml`
  - update default remote model names
- Modify: `D:\GitHub\auto\.github\workflows\compensate-report.yml`
  - update default remote model names
- Modify: `D:\GitHub\auto\config\litellm\litellm-config.example.yaml`
  - update example aliases to V4 names
- Modify: `D:\GitHub\auto\config\litellm\litellm-config.local.example.yaml`
  - update example aliases to V4 names
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
  - add legacy status migration and writable-field-first view ordering
- Modify: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`
  - cover status migration and first-screen view ordering
- Modify: `D:\GitHub\auto\tests\test_settings.py`
  - cover default DeepSeek model values
- Modify: `D:\GitHub\auto\tests\test_workflows.py`
  - cover workflow defaults

## Task 1: Migrate DeepSeek Defaults To V4 Routing

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\.github\workflows\reusable-analyze.yml`
- Modify: `D:\GitHub\auto\.github\workflows\reusable-report.yml`
- Modify: `D:\GitHub\auto\.github\workflows\compensate-report.yml`
- Modify: `D:\GitHub\auto\config\litellm\litellm-config.example.yaml`
- Modify: `D:\GitHub\auto\config\litellm\litellm-config.local.example.yaml`
- Test: `D:\GitHub\auto\tests\test_settings.py`
- Test: `D:\GitHub\auto\tests\test_workflows.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_load_settings_defaults_to_deepseek_v4_flash():
    settings = load_settings(Path.cwd())
    assert settings.env["AI_MODEL"] == "deepseek-v4-flash"


def test_workflow_defaults_prefer_deepseek_v4_flash_and_stage_pro_overrides():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-report.yml").read_text(encoding="utf-8")
    assert "AI_MODEL: ${{ vars.AI_MODEL || 'deepseek-v4-flash' }}" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_settings.py tests/test_workflows.py -k "deepseek_v4 or stage_pro" -q`
Expected: FAIL because the repo still defaults to `deepseek-chat`

- [ ] **Step 3: Write the minimal implementation**

```python
"AI_MODEL": os.environ.get("AI_MODEL", "deepseek-v4-flash"),
"ANALYSIS_AI_MODEL": os.environ.get("ANALYSIS_AI_MODEL", "deepseek-v4-pro"),
"SUMMARY_AI_MODEL": os.environ.get("SUMMARY_AI_MODEL", "deepseek-v4-pro"),
"FORECAST_AI_MODEL": os.environ.get("FORECAST_AI_MODEL", "deepseek-v4-pro"),
"PREFILTER_AI_MODEL": os.environ.get("PREFILTER_AI_MODEL", "deepseek-v4-flash"),
"DISCOVERY_AI_MODEL": os.environ.get("DISCOVERY_AI_MODEL", "deepseek-v4-flash"),
"SEARCH_AI_MODEL": os.environ.get("SEARCH_AI_MODEL", "deepseek-v4-flash"),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_settings.py tests/test_workflows.py -k "deepseek_v4 or stage_pro" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/settings.py .github/workflows/reusable-analyze.yml .github/workflows/reusable-report.yml .github/workflows/compensate-report.yml config/litellm/litellm-config.example.yaml config/litellm/litellm-config.local.example.yaml tests/test_settings.py tests/test_workflows.py
git commit -m "feat: move default deepseek routing to v4"
```

## Task 2: Migrate Existing Feishu Ops Desk Statuses And First-Screen Ordering

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- Test: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ops_desk_lead_review_first_screen_puts_status_and_note_first():
    fields = OPS_DESK_TABLE_SPECS["lead_review"]["views"][0]["fields"]
    assert fields[:2] == ["status", "note"]


def test_ops_desk_delivery_audit_first_screen_puts_writable_fields_first():
    fields = OPS_DESK_TABLE_SPECS["delivery_audit"]["views"][0]["fields"]
    assert fields[:3] == ["card_verified", "fallback_observed", "delivery_note"]


def test_build_lead_review_table_migrates_legacy_waiting_status():
    payload = _build_lead_review_table({
        "items": [{"title": "legacy", "status": "pending", "note": "", "priority_label": "high", "keyword": "", "bucket": "", "updated_at": "", "lead_key": "k", "priority_score": 10}]
    })
    assert payload["records"][0]["status"] == "待审批"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "first_screen or legacy_waiting_status" -q`
Expected: FAIL because the current visible-field order still leads with read-only context fields and legacy row payloads can still surface stale labels

- [ ] **Step 3: Write the minimal implementation**

```python
OPS_DESK_TABLE_SPECS["lead_review"]["views"][0]["fields"] = [
    "status", "note", "title", "priority_label", "keyword", "bucket", "updated_at", "lead_key"
]
OPS_DESK_TABLE_SPECS["delivery_audit"]["views"][0]["fields"] = [
    "card_verified", "fallback_observed", "delivery_note", "feishu_status", "generated_at", "publication_mode", "risk_level"
]
```

and add a small normalization helper that maps legacy display/repo statuses such as `待处理` to `待审批` during payload build and write-back.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "first_screen or legacy_waiting_status or pull_feishu_ops_status" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py tests/test_lark_cli_sidecar.py
git commit -m "feat: migrate feishu ops desk to first-screen writable layouts"
```

## Task 3: Full Verification

**Files:**
- Modify: none
- Test: `D:\GitHub\auto\tests\test_settings.py`
- Test: `D:\GitHub\auto\tests\test_workflows.py`
- Test: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`
- Test: `D:\GitHub\auto\tests\test_sources.py`

- [ ] **Step 1: Run focused verification**

Run: `python -m pytest tests/test_settings.py tests/test_workflows.py tests/test_lark_cli_sidecar.py -q`
Expected: PASS

- [ ] **Step 2: Run workflow validation**

Run: `pwsh ./scripts/check-workflows.ps1 -Profile full`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests -q`
Expected: PASS

- [ ] **Step 4: Commit any final doc/snapshot adjustments if needed**

```bash
git add -A
git commit -m "chore: verify deepseek v4 routing and feishu ops desk polish"
```
