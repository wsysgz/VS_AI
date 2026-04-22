# P3-B Feishu Ops Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first usable Feishu ops desk batch for VS_AI: sync four operator-facing datasets into Feishu, allow status-only pull-back for approvals and delivery audit, and keep repo JSON/config as the only source of truth.

**Architecture:** Extend the existing local Feishu sidecar instead of introducing a new runtime. Reuse repo truth artifacts (`run-status.json`, `source-governance.json`, `source-lead-review-status.json`, `candidate-updates.json`) to drive Feishu datasets, and introduce a separate status-only pull-back path that writes back to repo JSON but never directly mutates source config.

**Tech Stack:** Python, existing `lark-cli` integration, JSON state artifacts, pytest

---

## File Structure

- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
  - expand from report/governance sync into ops-desk sync + pull-back logic
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
  - add command handlers for ops-desk sync and status pull-back
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
  - add CLI commands for the first P3-B batch
- Create: `D:\GitHub\auto\data\state\delivery-audit-review.json`
  - canonical operator review overlay for delivery verification state
- Create: `D:\GitHub\auto\out\feishu-ops\latest-sync.json`
  - optional local snapshot of the exported ops-desk payload
- Modify: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`
  - add sync/pull-back coverage for ops desk
- Modify: `D:\GitHub\auto\tests\test_cli_smoke.py`
  - add CLI parsing coverage
- Modify: `D:\GitHub\auto\tests\test_run_once.py`
  - add delivery-audit overlay / command coverage as needed

## Task 1: Define Ops Desk Payload Builders

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- Test: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`

- [ ] **Step 1: Write the failing tests for payload shape**

```python
def test_build_ops_desk_payload_contains_four_tables(tmp_path):
    payload = _build_ops_desk_payload(tmp_path)

    assert set(payload) == {
        "governance_main",
        "lead_review",
        "delivery_audit",
        "candidate_updates",
    }


def test_build_delivery_audit_rows_merge_run_status_with_review_overlay(tmp_path):
    payload = _build_ops_desk_payload(tmp_path)
    rows = payload["delivery_audit"]["rows"]

    assert rows[0] == [
        "generated_at",
        "publication_mode",
        "risk_level",
        "feishu_status",
        "feishu_message_id",
        "card_verified",
        "fallback_observed",
        "delivery_note",
    ]
    assert len(rows) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "ops_desk_payload or delivery_audit_rows" -q`
Expected: FAIL because `_build_ops_desk_payload` and related helpers do not exist yet

- [ ] **Step 3: Write minimal payload builders**

```python
def _build_ops_desk_payload(root_dir: Path) -> dict[str, Any]:
    governance_payload = _load_governance_payload(root_dir)
    lead_review_payload = _load_json(root_dir / "out" / "review-queue" / "source-lead-review-status.json")
    candidate_updates_payload = _load_json(root_dir / "out" / "review-queue" / "candidate-updates.json")
    run_status_payload = _load_json(root_dir / "data" / "state" / "run-status.json")
    delivery_review_payload = _load_json(root_dir / "data" / "state" / "delivery-audit-review.json")
    return {
        "governance_main": _build_governance_main_table(governance_payload),
        "lead_review": _build_lead_review_table(lead_review_payload),
        "delivery_audit": _build_delivery_audit_table(run_status_payload, delivery_review_payload),
        "candidate_updates": _build_candidate_updates_table(candidate_updates_payload),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "ops_desk_payload or delivery_audit_rows" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py tests/test_lark_cli_sidecar.py
git commit -m "feat: add feishu ops desk payload builders"
```

## Task 2: Sync Four Ops Desk Tables Into Feishu

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- Test: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`

- [ ] **Step 1: Write the failing tests for ops desk sync**

```python
def test_sync_feishu_ops_desk_creates_base_and_tables(tmp_path, monkeypatch):
    result = sync_feishu_ops_desk(tmp_path, settings)

    assert result["base"]["app_token"] == "base_1"
    assert set(result["tables"]) == {
        "governance_main",
        "lead_review",
        "delivery_audit",
        "candidate_updates",
    }


def test_sync_feishu_ops_desk_persists_state(tmp_path, monkeypatch):
    result = sync_feishu_ops_desk(tmp_path, settings)
    state = _load_sidecar_state(tmp_path)

    assert state["ops_desk"]["base"]["app_token"] == result["base"]["app_token"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "ops_desk_creates_base or ops_desk_persists_state" -q`
Expected: FAIL because `sync_feishu_ops_desk` does not exist yet

- [ ] **Step 3: Implement minimal ops desk sync**

```python
def sync_feishu_ops_desk(root_dir: Path, settings) -> dict[str, Any]:
    state = _load_sidecar_state(root_dir)
    ops_state = dict(state.get("ops_desk", {}))
    payload = _build_ops_desk_payload(root_dir)
    base_meta = _ensure_ops_desk_base(root_dir, settings, ops_state)
    table_state = _sync_ops_desk_tables(root_dir, settings, base_meta, ops_state.get("tables", {}), payload)
    result = {
        "base": base_meta,
        "tables": table_state,
        "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    state["ops_desk"] = result
    _save_sidecar_state(root_dir, state)
    _save_ops_desk_snapshot(root_dir, payload, result)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "ops_desk_creates_base or ops_desk_persists_state" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py tests/test_lark_cli_sidecar.py
git commit -m "feat: sync feishu ops desk tables"
```

## Task 3: Pull Back Writable Statuses Only

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- Create: `D:\GitHub\auto\data\state\delivery-audit-review.json`
- Test: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`

- [ ] **Step 1: Write the failing tests for pull-back**

```python
def test_pull_feishu_ops_status_updates_lead_review_status_only(tmp_path, monkeypatch):
    result = pull_feishu_ops_status(tmp_path, settings)
    payload = json.loads((tmp_path / "out" / "review-queue" / "source-lead-review-status.json").read_text(encoding="utf-8"))

    target = next(item for item in payload["items"] if item["lead_key"] == "lead-1")
    assert target["status"] == "approved"
    assert target["note"] == "checked in Feishu"


def test_pull_feishu_ops_status_updates_delivery_audit_overlay(tmp_path, monkeypatch):
    result = pull_feishu_ops_status(tmp_path, settings)
    payload = json.loads((tmp_path / "data" / "state" / "delivery-audit-review.json").read_text(encoding="utf-8"))

    assert payload["items"][0]["card_verified"] is True
    assert payload["items"][0]["fallback_observed"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "pull_feishu_ops_status" -q`
Expected: FAIL because `pull_feishu_ops_status` does not exist yet

- [ ] **Step 3: Implement minimal status-only pull-back**

```python
def pull_feishu_ops_status(root_dir: Path, settings) -> dict[str, Any]:
    state = _load_sidecar_state(root_dir)
    ops_state = state.get("ops_desk", {})
    lead_rows = _read_ops_desk_rows(settings, ops_state["base"], ops_state["tables"]["lead_review"])
    delivery_rows = _read_ops_desk_rows(settings, ops_state["base"], ops_state["tables"]["delivery_audit"])
    lead_result = _write_back_lead_review_status(root_dir, lead_rows)
    delivery_result = _write_back_delivery_audit_review(root_dir, delivery_rows)
    return {"lead_review": lead_result, "delivery_audit": delivery_result}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "pull_feishu_ops_status" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py data/state/delivery-audit-review.json tests/test_lark_cli_sidecar.py
git commit -m "feat: pull feishu ops status into repo json"
```

## Task 4: Wire CLI And App Commands

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Test: `D:\GitHub\auto\tests\test_cli_smoke.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
def test_sync_feishu_ops_desk_command_exists():
    parser = build_parser()
    args = parser.parse_args(["sync-feishu-ops-desk"])
    assert args.command == "sync-feishu-ops-desk"


def test_pull_feishu_ops_status_command_exists():
    parser = build_parser()
    args = parser.parse_args(["pull-feishu-ops-status"])
    assert args.command == "pull-feishu-ops-status"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli_smoke.py -k "ops_desk_command_exists or pull_feishu_ops_status_command_exists" -q`
Expected: FAIL because parser does not know those commands

- [ ] **Step 3: Add minimal CLI/app wiring**

```python
ops_desk_parser = subparsers.add_parser(
    "sync-feishu-ops-desk",
    help="[Ops] Sync Feishu ops desk tables from repo truth",
)
pull_ops_parser = subparsers.add_parser(
    "pull-feishu-ops-status",
    help="[Ops] Pull writable Feishu ops desk statuses back into repo JSON",
)
```

and

```python
def cmd_sync_feishu_ops_desk(root_dir: Path) -> dict[str, object]:
    settings = load_settings(root_dir)
    return sync_feishu_ops_desk(root_dir, settings)


def cmd_pull_feishu_ops_status(root_dir: Path) -> dict[str, object]:
    settings = load_settings(root_dir)
    return pull_feishu_ops_status(root_dir, settings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli_smoke.py -k "ops_desk_command_exists or pull_feishu_ops_status_command_exists" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/cli.py src/auto_report/app.py tests/test_cli_smoke.py
git commit -m "feat: wire feishu ops desk commands"
```

## Task 5: Run Targeted Verification

**Files:**
- Modify: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`
- Modify: `D:\GitHub\auto\tests\test_cli_smoke.py`

- [ ] **Step 1: Run lark sidecar and CLI targeted tests**

Run:

```bash
$env:TEMP='D:\\GitHub\\auto\\output\\pytest-tmp'
$env:TMP='D:\\GitHub\\auto\\output\\pytest-tmp'
$env:PYTHONPATH='src'
python -m pytest tests/test_lark_cli_sidecar.py tests/test_cli_smoke.py -q
```

Expected: PASS

- [ ] **Step 2: Run one local dry-run outward sync**

Run:

```bash
$env:PYTHONPATH='src'
python -m auto_report.cli sync-feishu-ops-desk
```

Expected: success summary with base/table metadata written into `data/state/feishu-sidecar.json`

- [ ] **Step 3: Run one local pull-back sync**

Run:

```bash
$env:PYTHONPATH='src'
python -m auto_report.cli pull-feishu-ops-status
```

Expected: success summary with repo JSON status files updated only in writable fields

- [ ] **Step 4: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py src/auto_report/cli.py src/auto_report/app.py tests/test_lark_cli_sidecar.py tests/test_cli_smoke.py data/state/delivery-audit-review.json
git commit -m "feat: ship first p3b feishu ops desk batch"
```
