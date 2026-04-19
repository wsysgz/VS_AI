# LiteLLM Gateway First Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit optional LiteLLM Gateway path to the repo without removing the direct-provider fallback.

**Architecture:** Extend the existing OpenAI-compatible client with a named `litellm_proxy` provider, expose the gateway key in settings, and document the alias-based rollout. Keep the runtime HTTP path small and reuse existing stage routing instead of inventing a new client stack.

**Tech Stack:** Python, pytest, markdown docs, LiteLLM proxy config YAML.

---

## File Map

- Create: `D:\GitHub\auto\config\litellm\litellm-config.example.yaml`
- Create: `D:\GitHub\auto\docs\superpowers\specs\2026-04-19-litellm-gateway-first-rollout-design.md`
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\.env.example`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AGENTS.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\V1升级方案.md`
- Test: `D:\GitHub\auto\tests\test_llm_client.py`
- Test: `D:\GitHub\auto\tests\test_settings.py`

### Task 1: Add failing tests for the gateway contract

**Files:**
- Modify: `D:\GitHub\auto\tests\test_llm_client.py`
- Modify: `D:\GitHub\auto\tests\test_settings.py`

- [ ] **Step 1: Add provider-resolution tests**
- [ ] **Step 2: Run `python -m pytest tests/test_llm_client.py tests/test_settings.py -q`**
- [ ] **Step 3: Confirm failure is caused by missing `litellm_proxy` defaults and missing `LITELLM_MASTER_KEY` exposure**

### Task 2: Implement the minimal runtime contract

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\integrations\llm_client.py`
- Modify: `D:\GitHub\auto\src\auto_report\settings.py`
- Modify: `D:\GitHub\auto\.env.example`

- [ ] **Step 1: Add `litellm_proxy` to provider defaults**
- [ ] **Step 2: Expose `LITELLM_MASTER_KEY` in settings and `.env.example`**
- [ ] **Step 3: Re-run targeted tests and confirm green**

### Task 3: Document the staged rollout

**Files:**
- Create: `D:\GitHub\auto\config\litellm\litellm-config.example.yaml`
- Modify: `D:\GitHub\auto\README.md`
- Modify: `D:\GitHub\auto\AGENTS.md`
- Modify: `D:\GitHub\auto\AI对接手册.md`
- Modify: `D:\GitHub\auto\V1升级方案.md`

- [ ] **Step 1: Document the new `litellm_proxy` provider and alias examples**
- [ ] **Step 2: Add the stage-discipline rule**
- [ ] **Step 3: Place Feishu push cards in `P3-A` and Feishu bitable in `P3-B`**

### Task 4: Verify

**Files:**
- Verify only

- [ ] **Step 1: Run `python -m pytest tests/test_llm_client.py tests/test_settings.py -q`**
- [ ] **Step 2: Run an adjacent smoke test if needed**
- [ ] **Step 3: Check `git diff --stat` and confirm every change maps back to this rollout**
