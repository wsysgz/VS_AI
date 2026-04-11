# Documentation consolidation design

**Date:** 2026-04-11  
**Topic:** formal documentation authority for the VS_AI takeover

## Goals

- Give each document a single, well-defined authority so maintainers no longer find the same tasks described in multiple places.
- Fold the DeepSeek/AI configuration guidance into the formal manuals instead of keeping a standalone `DEEPSEEK_SETUP.md`, and make sure the fallback-to-rule-summary behavior is documented.
- Remove the obsolete `D:\AI\workbuddy\auto\auto` workspace references and keep the new docs aligned with the product promise (daily Beijing 07:00 report, PushPlus/WeChat short summary, Telegram full report, Feishu full report).
- Verify the cleanup by running `rg -n "D:\\AI\\workbuddy\\auto\\auto|D:/AI/workbuddy/auto/auto" README.md docs/HANDOFF.md docs/USER_GUIDE.md docs/TECHNICAL_GUIDE.md docs/ARCHITECTURE.md docs/push-channels-guide.md` after the edits.

## Document authority map

1. `README.md` – the primary entry point: top-level project overview, quick-start steps, the product promise, and explicit links to the remaining formal docs (	User Guide, Technical Guide, Architecture, Push Channels). Keep instructions concise and avoid detailed env or AI config tables.
2. `docs/HANDOFF.md` – the maintainer checklist: point readers to README plus each of the formal guides, summarize the audit material (e.g., `docs/superpowers/` and `docs/upgrade-plan-v6/`), and include a short maintenance checklist (what to read first, where to find tests/pipelines) without duplicating content.
3. `docs/USER_GUIDE.md` – ongoing operations and verification: how to run locally (venv, run-once, backfill), how to interpret outputs/data, how to check scheduled runs, and how to respond to channel failures. Mention the product promise and include reminders about verifying the daily Beijing 07:00 workflow.
4. `docs/TECHNICAL_GUIDE.md` – configuration and internals: environment variables, the AI configuration requirements (DEEPSEEK_API_KEY, AI_PROVIDER, AI_BASE_URL, AI_MODEL, AI_MAX_ANALYSIS_TOPICS, AUTOMATION toggles), and the fallback-to-rule-summary behavior when the AI key is missing. This is also the place to document how the LLM client chooses a provider and what defaults the code assumes.
5. `docs/ARCHITECTURE.md` – system structure: the StageTimer stages, pipeline (collect → dedup → classification → AI → rendering → push → archive), directory layout, important modules (integrations, outputs, etc.), and why they are decoupled. Also mention how data flows are captured (run-status, data/reports, etc.).
6. `docs/push-channels-guide.md` – messaging channels: how PushPlus, Telegram, and Feishu are configured, what env vars they rely on, what gets pushed (short summary vs full report), and how to validate deliveries. Reinforce that WeChat short summary uses PushPlus at Beijing 07:00 while Telegram/Feishu get full reports.

## AI configuration/DeepSeek guidance integration

- Remove `docs/DEEPSEEK_SETUP.md` (if it exists) and move its guidance into the Technical Guide.
- In the Technical Guide: spell out `DEEPSEEK_API_KEY` is required for the AI pipeline, `AI_PROVIDER` defaults to `deepseek` but can switch to `openai`, `AI_BASE_URL` overrides the API endpoint, `AI_MODEL` defaults to `deepseek-chat`, and `AI_MAX_ANALYSIS_TOPICS` throttles the amount of analysis (default 6).
- Describe the fallback-to-rule-summary mode that kicks in when no `DEEPSEEK_API_KEY` is defined or when the API repeatedly fails, so new maintainers understand why the system still runs.
- Mention how settings derived from `.env.example` connect to the code (e.g., `settings.py` loads `AI_BASE_URL`, `integrations/llm_client.py` chooses provider). Highlight that the fallback still runs even if DeepSeek is missing, so the daily report remains available, albeit without AI extras.

## Implementation steps

1. Draft the README to emphasize the quick-start, product promise, and explicit links to the new guides; remove the old `D:\AI\workbuddy\auto\auto` path.
2. Turn `docs/HANDOFF.md` into a navigator that points maintainers to README, USER_GUIDE, TECHNICAL_GUIDE, ARCHITECTURE, and push-channels-guide while explaining what to read next. Strip out the former deep content that now lives elsewhere.
3. Create `docs/USER_GUIDE.md`, `docs/TECHNICAL_GUIDE.md`, `docs/ARCHITECTURE.md`, and `docs/push-channels-guide.md` with the responsibilities defined above, ensuring no verbatim copy across files.
4. Remove (or confirm absence of) `docs/DEEPSEEK_SETUP.md` and any references to the obsolete workspace path.
5. After writing, run `rg` as described to confirm no old workspace paths remain in the formal docs.
6. Summarize the final state in the commit and mention the `rg` verification.

## Questions / assumptions

- I am assuming the AI config guidance should live primarily inside the Technical Guide and that README/HANDOFF should only reference it rather than repeat the details. Please confirm if any of the env variable guidance should remain at the top level before I move ahead.

## Self-review checklist

- [ ] Each formal doc has a single authority and there is no duplicated verbatim guidance in the others.
- [ ] All AI config variables and fallback behavior are documented in the Technical Guide.
- [ ] `docs/superpowers/` and `docs/upgrade-plan-v6/` remain untouched except for the new spec file.
- [ ] The `rg` cleanup command reports zero hits.
