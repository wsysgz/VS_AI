# Source Governance Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the repo-local governance loop by applying safe approved source updates back into source configs, promoting high-priority watch items into a repo-local registry, and running a repo-native watch runner without third-party changedetection dependencies.

**Architecture:** Keep source governance snapshots in `source_governance.py`, add a repo-local watch registry plus a local watch runner, generate actionable source/watch updates from `review_queue.py`, let `pipeline/source_updates.py` activate local watches, and expose watch-run results through CLI and dashboard artifacts.

**Tech Stack:** Python 3.11+, PyYAML, pytest, existing RSS/website/GitHub collectors.

---

### Task 1: Tighten approved lead update classification

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\review_queue.py`
- Modify: `D:\GitHub\auto\tests\test_review_queue.py`

- [ ] **Step 1: Write failing tests for safe apply readiness and source id resolution**
- [ ] **Step 2: Run `python -m pytest tests/test_review_queue.py -q` and verify the new tests fail for the expected reason**
- [ ] **Step 3: Update `review_queue.py` to prefer `meta.source_id`, block unsafe updates, and keep `rsshub` review-only**
- [ ] **Step 4: Re-run `python -m pytest tests/test_review_queue.py -q` and verify green**

### Task 2: Add source update apply engine

**Files:**
- Create: `D:\GitHub\auto\src\auto_report\pipeline\source_updates.py`
- Create: `D:\GitHub\auto\tests\test_source_updates.py`

- [ ] **Step 1: Write failing tests for applying `official_feed`, `validated_listing`, and `changedetection` updates into temp source configs**
- [ ] **Step 2: Run `python -m pytest tests/test_source_updates.py -q` and verify the tests fail because the module/behavior does not exist yet**
- [ ] **Step 3: Implement the minimal YAML load/merge/write helpers and apply engine**
- [ ] **Step 4: Re-run `python -m pytest tests/test_source_updates.py -q` and verify green**

### Task 3: Wire CLI and app command

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\tests\test_cli_smoke.py`

- [ ] **Step 1: Write failing CLI smoke coverage for `apply-source-updates`**
- [ ] **Step 2: Run `python -m pytest tests/test_cli_smoke.py -q` and verify the new assertion fails**
- [ ] **Step 3: Implement the new CLI/app entrypoint and post-apply artifact rebuild hook**
- [ ] **Step 4: Re-run `python -m pytest tests/test_cli_smoke.py -q` and verify green**

### Task 4: Add local watch registry and dashboard visibility

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\outputs\source_governance.py`
- Modify: `D:\GitHub\auto\src\auto_report\outputs\ops_dashboard.py`
- Modify: `D:\GitHub\auto\tests\test_source_governance_output.py`
- Modify: `D:\GitHub\auto\tests\test_ops_dashboard.py`

- [ ] **Step 1: Write failing tests for registry sync and dashboard rendering**
- [ ] **Step 2: Run `python -m pytest tests/test_source_governance_output.py tests/test_ops_dashboard.py -q` and verify the new assertions fail**
- [ ] **Step 3: Implement registry generation, state preservation, and dashboard sections**
- [ ] **Step 4: Re-run `python -m pytest tests/test_source_governance_output.py tests/test_ops_dashboard.py -q` and verify green**

### Task 5: Add repo-native watch runner

**Files:**
- Create: `D:\GitHub\auto\src\auto_report\pipeline\watch_runner.py`
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Create: `D:\GitHub\auto\tests\test_watch_runner.py`
- Modify: `D:\GitHub\auto\tests\test_cli_smoke.py`

- [ ] **Step 1: Write failing tests for baseline initialization and changed-item detection**
- [ ] **Step 2: Run `python -m pytest tests/test_watch_runner.py tests/test_cli_smoke.py -q` and verify the new assertions fail**
- [ ] **Step 3: Implement `run-watch-checks` and baseline/result artifacts for `active_local` watch items**
- [ ] **Step 4: Re-run `python -m pytest tests/test_watch_runner.py tests/test_cli_smoke.py -q` and verify green**

### Task 6: Verify the end-to-end local closure loop

**Files:**
- Modify if needed: `D:\GitHub\auto\docs\superpowers\specs\2026-04-21-source-governance-closure-design.md`
- Modify if needed: `D:\GitHub\auto\docs\superpowers\plans\2026-04-21-source-governance-closure.md`

- [ ] **Step 1: Run targeted governance tests together**
- [ ] **Step 2: Run `apply-source-updates` in real mode so planned watch items become `active_local`**
- [ ] **Step 3: Run `run-watch-checks` to initialize or compare local watch baselines**
- [ ] **Step 3: Run `python -m pytest tests -q`**
- [ ] **Step 4: Record what changed, what remains intentionally manual, and which updates were applied vs blocked**
