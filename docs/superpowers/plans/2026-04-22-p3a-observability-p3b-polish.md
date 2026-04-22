# P3-A Observability + P3-B Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit Feishu card-vs-text delivery observability to `run-status.json`, and tighten the first Feishu ops desk batch with second-round Chinese-first polish.

**Architecture:** Keep the existing pipeline boundaries. `P3-A` observability stays in the delivery-status / run-status path, while `P3-B` polish stays inside the Feishu sidecar table spec and row/view presentation. Do not introduce new runtime state beyond the existing repo JSON artifacts.

**Tech Stack:** Python, JSON state artifacts, pytest, existing Feishu sidecar integration

---

## File Structure

- Modify: `D:\GitHub\auto\src\auto_report\integrations\feishu.py`
  - annotate card success vs text fallback in the Feishu send path
- Modify: `D:\GitHub\auto\src\auto_report\integrations\delivery_status.py`
  - preserve optional Feishu delivery-kind metadata in channel summaries
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
  - surface the Feishu delivery-kind signal in delivery diagnostics
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\run_once.py`
  - write the new signal into `data/state/run-status.json`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
  - apply second-round ops desk polish (Chinese-first naming, field ordering, and visible views)
- Modify: `D:\GitHub\auto\tests\test_run_once.py`
  - cover run-status delivery observability and diagnose-delivery behavior
- Modify: `D:\GitHub\auto\tests\test_delivery_status.py`
  - cover channel summary preservation of delivery-kind metadata
- Modify: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`
  - cover the ops desk polish expectations

## Task 1: Add Feishu Card/Text Delivery Observability

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\feishu.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\delivery_status.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\run_once.py`
- Modify: `D:\GitHub\auto\tests\test_delivery_status.py`
- Modify: `D:\GitHub\auto\tests\test_run_once.py`

- [ ] **Step 1: Write failing tests for delivery-kind preservation**

```python
def test_build_channel_result_preserves_delivery_kind():
    result = build_channel_result(
        "feishu",
        configured=True,
        attempted=True,
        ok=True,
        detail="success",
        delivery_kind="card_success",
    )

    assert result["delivery_kind"] == "card_success"


def test_build_run_status_includes_feishu_delivery_kind():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        push_response={
            "feishu": [
                {
                    "code": 0,
                    "msg": "success",
                    "data": {"message_id": "om_1"},
                    "delivery_kind": "text_fallback",
                }
            ]
        },
    )

    assert status["push_response"]["feishu"]["delivery_kind"] == "text_fallback"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_delivery_status.py tests/test_run_once.py -k "delivery_kind or feishu_delivery_kind" -q`
Expected: FAIL because the delivery-kind field does not exist yet

- [ ] **Step 3: Implement minimal delivery-kind propagation**

```python
def build_channel_result(..., delivery_kind: str = "") -> dict[str, object]:
    result = {
        ...
    }
    if delivery_kind:
        result["delivery_kind"] = delivery_kind
    return result


def _summarize_feishu_response(push_response: object) -> dict[str, object]:
    ...
    delivery_kind = ""
    for item in responses:
        ...
        if not delivery_kind and isinstance(item.get("delivery_kind"), str):
            delivery_kind = item["delivery_kind"]
    ...
    if delivery_kind:
        summary["delivery_kind"] = delivery_kind
    return summary
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_delivery_status.py tests/test_run_once.py -k "delivery_kind or feishu_delivery_kind" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/feishu.py src/auto_report/integrations/delivery_status.py src/auto_report/pipeline/run_once.py tests/test_delivery_status.py tests/test_run_once.py
git commit -m "feat: add feishu delivery observability"
```

## Task 2: Polish P3-B Feishu Ops Desk

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\lark_cli.py`
- Modify: `D:\GitHub\auto\tests\test_lark_cli_sidecar.py`

- [ ] **Step 1: Write failing tests for Chinese-first polish**

```python
def test_ops_desk_table_specs_use_chinese_first_labels():
    assert OPS_DESK_TABLE_SPECS["lead_review"]["name"] == "审批协作"
    assert OPS_DESK_TABLE_SPECS["delivery_audit"]["views"][0]["name"] == "待验收"
    assert OPS_DESK_TABLE_SPECS["candidate_updates"]["views"][0]["name"] == "待应用变更"


def test_delivery_audit_field_order_prioritizes_verification_fields():
    fields = OPS_DESK_TABLE_SPECS["delivery_audit"]["fields"]
    assert fields[:6] == [
        "generated_at",
        "publication_mode",
        "feishu_status",
        "card_verified",
        "fallback_observed",
        "delivery_note",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "Chinese_first_labels or delivery_audit_field_order" -q`
Expected: FAIL if the field/view ordering is not aligned

- [ ] **Step 3: Apply minimal polish to table specs**

```python
OPS_DESK_TABLE_SPECS["lead_review"]["views"] = [
    {"name": "待审批", ...},
    {"name": "已批准", ...},
    {"name": "已延后", ...},
    {"name": "最近更新", ...},
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lark_cli_sidecar.py -k "Chinese_first_labels or delivery_audit_field_order or ops_desk" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/lark_cli.py tests/test_lark_cli_sidecar.py
git commit -m "feat: polish feishu ops desk views"
```
