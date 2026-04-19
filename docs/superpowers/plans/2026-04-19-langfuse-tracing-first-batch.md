# Langfuse Tracing First Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add metadata-first Langfuse tracing to the main `run-once` pipeline, stage timers, and LLM calls without uploading prompt/response content by default.

**Architecture:** Introduce a small tracing adapter under `integrations/` that owns all Langfuse-specific behavior. The app and pipeline layers only call adapter functions to start/finish root traces, stage spans, and LLM generations. This keeps the main pipeline readable and lets tracing remain optional.

**Tech Stack:** Python, Langfuse Python SDK, pytest, existing `run-status.json` pipeline.

---

## File Map

- Create: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\ai_pipeline.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\run_once.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\requirements.txt`
- Modify: `D:\GitHub\auto\.env.example`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\用户操作手册.md`
- Test: `D:\GitHub\auto\tests\test_langfuse_tracing.py`
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`
- Test: `D:\GitHub\auto\tests\test_run_once.py`

### Task 1: Add failing tests for tracing settings and status payload

**Files:**
- Modify: `D:\GitHub\auto\tests\test_settings.py`
- Modify: `D:\GitHub\auto\tests\test_run_once.py`

- [ ] **Step 1: Add tests for `LANGFUSE_*` env exposure**
- [ ] **Step 2: Add tests for `build_run_status(..., tracing=...)`**
- [ ] **Step 3: Run targeted tests and confirm failure**

### Task 2: Add tracing adapter and its unit tests

**Files:**
- Create: `D:\GitHub\auto\src\auto_report\integrations\langfuse_tracing.py`
- Create: `D:\GitHub\auto\tests\test_langfuse_tracing.py`

- [ ] **Step 1: Add failing tests for enablement, metadata-first capture, and stage span parenting**
- [ ] **Step 2: Implement a minimal adapter with lazy Langfuse loading**
- [ ] **Step 3: Re-run adapter tests and confirm green**

### Task 3: Hook tracing into app, AI pipeline, and LLM client

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\pipeline\ai_pipeline.py`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`

- [ ] **Step 1: Add a failing test for LLM tracing hooks**
- [ ] **Step 2: Add root trace and pipeline spans**
- [ ] **Step 3: Add stage spans and generation observations**
- [ ] **Step 4: Verify targeted tests pass**

### Task 4: Document and package the feature

**Files:**
- Modify: `D:\GitHub\auto\requirements.txt`
- Modify: `D:\GitHub\auto\.env.example`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\用户操作手册.md`

- [ ] **Step 1: Add `langfuse` dependency and env examples**
- [ ] **Step 2: Document metadata-first behavior and optional content capture**
- [ ] **Step 3: Re-run focused tests and smoke the non-tracing path**
