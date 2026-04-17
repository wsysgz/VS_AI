# AI Source Stability First Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize the first batch of official AI source pages by upgrading `deepseek-updates` and `moonshot-blog` from generic listing extraction to structured page extraction and matching governance defaults.

**Architecture:** Introduce a dedicated structured website extraction path that reads per-source entry selectors and dispatches from the website collector by source mode. Treat the migrated structured pages as direct official polling targets instead of replacement candidates.

**Tech Stack:** Python, pytest, BeautifulSoup, YAML source configs

---

### Task 1: Add parser coverage for structured website pages

**Files:**
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Write the failing structured extraction test**
- [ ] **Step 2: Run the targeted source tests and confirm the new test fails**
- [ ] **Step 3: Add the minimal production parser code**
- [ ] **Step 4: Re-run the targeted source tests and confirm the parser test passes**

### Task 2: Add governance expectations for structured official pages

**Files:**
- Modify: `tests/test_source_registry.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Write failing assertions for the migrated source modes and governance defaults**
- [ ] **Step 2: Run targeted tests and confirm the new assertions fail**
- [ ] **Step 3: Update registry/config code minimally**
- [ ] **Step 4: Re-run the targeted tests and confirm they pass**

### Task 3: Implement the structured collector path and migrate the first batch

**Files:**
- Modify: `src/auto_report/sources/websites.py`
- Modify: `src/auto_report/sources/collector.py`
- Modify: `src/auto_report/source_registry.py`
- Modify: `config/sources/websites.yaml`

- [ ] **Step 1: Dispatch the website collector by mode**
- [ ] **Step 2: Implement structured extraction using entry/title/link/date selectors**
- [ ] **Step 3: Migrate `deepseek-updates` and `moonshot-blog` to the new mode and selectors**
- [ ] **Step 4: Keep the rest of the website sources unchanged**

### Task 4: Verify the batch end-to-end

**Files:**
- Verify only: `tests/test_sources.py`
- Verify only: `tests/test_source_registry.py`
- Verify only: `tests/test_settings.py`

- [ ] **Step 1: Run targeted pytest for source parsing, settings, and registry**
- [ ] **Step 2: Run a small local collection check for website sources**
- [ ] **Step 3: Summarize which first-batch sources are now direct stable page polls**
