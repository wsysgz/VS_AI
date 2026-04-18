# P1 Governance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn source governance into a watch-ready, priority-ranked operational artifact and surface it in the ops dashboard so P1 can close cleanly.

**Architecture:** Extend the existing `source_registry -> source_governance -> ops_dashboard` flow instead of introducing new services or storage. Add a deterministic priority model, a concrete changedetection watch list, and a merged governance queue while preserving existing grouped governance output.

**Tech Stack:** Python, existing source governance artifact generation, ops dashboard HTML rendering, pytest.

---

## File Map

- Modify: `D:\GitHub\auto\src\auto_report\source_registry.py`
- Modify: `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
- Modify: `D:\GitHub\auto\V1升级方案.md`
- Test: `D:\GitHub\auto\tests\test_source_registry.py`
- Test: `D:\GitHub\auto\tests\test_ops_dashboard.py`

### Task 1: Add governance priority scoring and changedetection watch rows

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\source_registry.py`
- Test: `D:\GitHub\auto\tests\test_source_registry.py`

- [ ] **Step 1: Write the failing tests**

Add tests that assert:

```python
assert "priority_queue" in governance
assert "changedetection_watch_list" in governance
assert governance["priority_queue"][0]["priority_score"] >= governance["priority_queue"][-1]["priority_score"]
assert all("watch_target" in item for item in governance["changedetection_watch_list"])
```

- [ ] **Step 2: Run the targeted tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_source_registry.py -q
```

Expected: FAIL because the new keys and operational fields do not exist yet.

- [ ] **Step 3: Implement the minimal scoring helpers**

In `D:\GitHub\auto\src\auto_report\source_registry.py`, add small helper functions for:

```python
def _priority_score(row: dict[str, object]) -> int: ...
def _priority_label(score: int) -> str: ...
def _priority_reason(row: dict[str, object], score: int) -> str: ...
```

Keep them deterministic and additive.

- [ ] **Step 4: Extend `build_source_governance_queue(...)`**

Add:

- `changedetection_watch_list`
- `priority_queue`

Each row should include:

```python
{
    "source_id": ...,
    "candidate_kind": ...,
    "priority_score": ...,
    "priority_label": ...,
    "reason": ...,
    "watch_target": ...,
    "next_action": ...,
    "url": ...,
}
```

- [ ] **Step 5: Re-run targeted tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_source_registry.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/source_registry.py tests/test_source_registry.py
git commit -m "feat: add governance priority queue"
```

### Task 2: Surface the governance priority queue in the ops dashboard

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
- Test: `D:\GitHub\auto\tests\test_ops_dashboard.py`

- [ ] **Step 1: Write the failing dashboard test**

Add a test that verifies the rendered HTML contains:

```python
assert "Governance Priority Queue" in html
assert "priority_score" in html or "Priority" in html
```

- [ ] **Step 2: Run the targeted dashboard test and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_ops_dashboard.py -q
```

Expected: FAIL because the section does not exist yet.

- [ ] **Step 3: Implement the minimal render path**

In `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`:

- add a small render helper for the merged queue
- insert a new section before the raw grouped governance tables
- reuse existing table styling where possible

- [ ] **Step 4: Re-run the targeted dashboard test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_ops_dashboard.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/outputs/ops_dashboard.py tests/test_ops_dashboard.py
git commit -m "feat: add governance priority section to ops dashboard"
```

### Task 3: Update the P1 plan status after implementation lands

**Files:**
- Modify: `D:\GitHub\auto\V1升级方案.md`

- [ ] **Step 1: Re-read the current unchecked P1 items**

Verify whether these lines are now truly complete:

- `第一版 changedetection.io watch 清单`
- `将治理队列进一步转成运维优先级视图`
- `P1 运营尾项仍未全部完成（RSSHub / changedetection / 治理优先级视图）`

- [ ] **Step 2: Update only status lines supported by fresh evidence**

If implementation and tests are complete, mark:

- changedetection watch list complete
- governance priority view complete

Keep RSSHub-related residual items unchecked if they are still incomplete.

- [ ] **Step 3: Commit**

```bash
git add V1升级方案.md
git commit -m "docs: mark p1 governance closure progress"
```

### Task 4: Final verification and artifact rebuild

**Files:**
- Verify only

- [ ] **Step 1: Run targeted tests**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_source_registry.py tests/test_ops_dashboard.py -q
```

Expected: PASS.

- [ ] **Step 2: Rebuild governance artifact**

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-source-governance
```

Expected: `out/source-governance/source-governance.json` updates successfully.

- [ ] **Step 3: Rebuild ops dashboard**

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-ops-dashboard
```

Expected: `out/ops-dashboard/index.html` updates successfully.

- [ ] **Step 4: Run full test suite**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 5: Commit verification checkpoint**

```bash
git status --short
git commit --allow-empty -m "chore: verify p1 governance closure"
```
