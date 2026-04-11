# Channel Template Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Formalize PushPlus, Feishu, and Telegram as short / medium / long delivery templates while keeping one shared executive brief source.

**Architecture:** Extend the existing renderer layer instead of adding a new delivery abstraction. `compose_executive_brief()` remains the semantic source of truth, while `renderers.py` exposes explicit channel renderers and `app.py` routes each channel to its intended output shape. Update maintainer docs so the runtime contract and the roadmap stay aligned.

**Tech Stack:** Python 3.14, pytest, existing `auto_report` renderers/app modules, Markdown docs.

---

### Task 1: Lock The Channel Template Contract In Tests

**Files:**
- Modify: `tests/test_renderers.py`

- [ ] **Step 1: Write the failing test**

```python
def test_render_pushplus_notification_uses_short_shape():
    text = render_pushplus_notification(
        title="AI情报早报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "今日判断：" in text
    assert "三条主线：" in text
    assert "详情链接：" in text
    assert "执行摘要" not in text
    assert "重点主题" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_renderers.py::test_render_pushplus_notification_uses_short_shape -q`
Expected: FAIL because `render_pushplus_notification()` does not yet exist.

- [ ] **Step 3: Write minimal implementation**

```python
def render_pushplus_notification(...):
    ...

def render_text_notification(...):
    return render_pushplus_notification(...)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_renderers.py::test_render_pushplus_notification_uses_short_shape -q`
Expected: PASS

### Task 2: Route The App Through Explicit Channel Renderers

**Files:**
- Modify: `src/auto_report/outputs/renderers.py`
- Modify: `src/auto_report/app.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing integration expectation**

```python
assert captured["content"].startswith("AI情报早报 |")
assert "执行摘要" not in captured["content"]
```

- [ ] **Step 2: Run targeted tests to verify mismatch**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_renderers.py tests/test_run_once.py -q`
Expected: FAIL if the explicit PushPlus renderer is not wired through app helpers.

- [ ] **Step 3: Write minimal implementation**

```python
from auto_report.outputs.renderers import render_pushplus_notification

def _build_text_notification(root_dir: Path, settings) -> str:
    ...
    return render_pushplus_notification(...)
```

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_renderers.py tests/test_run_once.py -q`
Expected: PASS

### Task 3: Align Maintainer Docs And Phase 10 Status Wording

**Files:**
- Modify: `README.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/OPS_RUNBOOK.md`
- Modify: `docs/push-channels-guide.md`
- Modify: `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`

- [ ] **Step 1: Update channel-role wording**

```text
PushPlus = short
Feishu = medium
Telegram = long
```

- [ ] **Step 2: Update the roadmap wording**

```text
channel roles are now separated as short / medium / long
remaining gap is richer per-channel variants, not basic separation
```

- [ ] **Step 3: Verify docs read consistently**

Run: `rg -n "完整报告正文|完整报告|中长度|短摘要|长文" README.md docs`
Expected: wording is internally consistent with the implemented channel roles.

### Task 4: Full Verification

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run the focused renderer and delivery tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_renderers.py tests/test_run_once.py -q`
Expected: PASS

- [ ] **Step 2: Run the full suite**

Run: `$env:PYTHONPATH='src'; python -m pytest tests -q`
Expected: PASS

- [ ] **Step 3: Record execution notes**

```text
- channel template layer now uses explicit short / medium / long roles
- semantic content still comes from compose_executive_brief()
- dual-track publishing remains a later Phase 10 slice
```
