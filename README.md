# VS_AI

VS_AI is an engineering-focused daily AI intelligence pipeline that collects signals, builds structured analysis, publishes multi-channel reports, and maintains a public reading site.

VS_AI 是一个工程化的每日 AI 情报生产系统，负责采集多源信号、生成结构化分析、输出多渠道报告，并持续维护公开阅读站。

Public site / 公开站入口:
`https://wsysgz.github.io/VS_AI/`

## Snapshot / 项目快照

- Workspace / 本地工作区:
  - `D:\GitHub\auto`
- Canonical remote / 目标远端:
  - `git@github.com:wsysgz/VS_AI.git`
- Focus / 关注领域:
  - AI / LLM / Agent
  - AI x Electronics
- Publication modes / 发布轨:
  - `auto`
  - `reviewed`
- Notification rule / 推送规则:
  - every notification includes the public site entry
  - every notification includes the matching GitHub raw report link
- Verification baseline / 当前验证基线:
  - `312 passed`
- Current project phase / 当前阶段:
  - `P2 核心能力（routing / gateway / tracing / fallback / budget）已验证`
  - `来源治理尾项已基本收口：repo-local watch runner / watch registry / candidate-updates / apply-source-updates 已打通`
  - `P3-A 已完成首轮发布级验收：飞书静态卡片 + 文本 fallback 已真实验证`
  - `P3-B 已正式纳入计划：飞书多维表格运营台将基于现有 sidecar 铺底扩展`
  - `当前尾项仅剩：renesas-blog 仍为 blocked（403）`

## What It Does / 系统能力

- Collects from RSS, GitHub, Hacker News, and curated websites.
- Deduplicates, scores, clusters, and builds topic packages for report generation.
- Runs AI analysis, summary, and forecast stages with unified `ai_metrics`.
- Publishes Markdown, HTML, JSON, PushPlus, Feishu, and Telegram outputs.
- Builds a public Pages site with archives, weekly pages, special topics, feed, and RSS.
- Exposes delivery, review, risk, and source health signals through `run-status.json`.

## Manual Map / 手册分工

- [AI对接手册.md](AI对接手册.md)
  - 面向开发、运维、交接，也是新会话 AI / 新维护者恢复上下文的第一入口。
- [用户操作手册.md](用户操作手册.md)
  - 面向使用者和值班同学，讲清楚怎么启动、怎么跑日报、怎么查看结果、怎么做常见操作。
- [V1升级方案.md](V1升级方案.md)
  - 面向后续优化升级，汇总可直接复用的外部项目、推荐技术路线和分阶段改造计划。
- [交接备忘录.md](交接备忘录.md)
  - 面向下一次接手或新会话恢复，快速说明当前状态、关键决策、遗留问题和下一步执行顺序。
- [AGENTS.md](AGENTS.md)
  - 面向代理和自动化协作，记录本仓库的工程约束与验证基线。

## Quick Start / 快速开始

### 1. Prepare the environment / 准备环境

```powershell
cd D:\GitHub\auto
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```

Fill `.env` with the keys you need / 在 `.env` 中补齐需要的配置:

- AI:
  - `DEEPSEEK_API_KEY`
  - or `OPENAI_API_KEY` / `AI_API_KEY`
  - `LITELLM_MASTER_KEY`
  - `LANGFUSE_ENABLED`
  - `LANGFUSE_PUBLIC_KEY`
  - `LANGFUSE_SECRET_KEY`
  - `LANGFUSE_BASE_URL`
  - `AI_PROVIDER`
  - `AI_BASE_URL`
  - `AI_MODEL`
- Delivery:
  - `PUSHPLUS_TOKEN`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `FEISHU_APP_ID`
  - `FEISHU_APP_SECRET`
  - `FEISHU_CHAT_ID`
  - `FEISHU_SIDECAR_ENABLED`
  - `FEISHU_DOC_WIKI_SPACE`
  - `FEISHU_GOVERNANCE_TASK_LIMIT`
  - `LARK_CLI_PATH`
  - `LARK_CLI_PROFILE`

Recommended provider examples / 推荐可直接复用的模型配置示例:

```env
# Option A: DeepSeek official (default / 当前主力推荐)
AI_PROVIDER=deepseek
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=<your-deepseek-key>

# Option B: MiniMax-M2.7 via OpenAI-compatible third-party endpoint
# Note: current repo supports one active provider per run. Switch the env
# values before execution; do not enable both providers in the same run yet.
AI_PROVIDER=minimax_svips
AI_BASE_URL=https://api.svips.org/v1
AI_MODEL=MiniMax-M2.7
AI_API_KEY=<your-minimax-key>

# Option C: LiteLLM Gateway (optional first-rollout path)
# Keep direct-provider mode as the default fallback; do not force every
# environment onto LiteLLM until the gateway path is locally verified.
AI_PROVIDER=litellm_proxy
AI_BASE_URL=http://127.0.0.1:4000
AI_MODEL=vs-ai-default
LITELLM_MASTER_KEY=sk-change-me
```

Current capability note / 当前能力说明:

- The current `llm_client.py` already supports OpenAI-compatible providers.
- The repo now has a first-class LiteLLM gateway provider contract via
  `AI_PROVIDER=litellm_proxy`.
- DeepSeek and MiniMax can coexist in configuration, but only one provider is
  active globally by default.
- Stage-level routing is now supported via environment overrides. Example:
- Recommended P2 stage ownership:
  - `analysis` -> DeepSeek
  - `summary` -> MiniMax-M2.7
  - `forecast` -> DeepSeek
  - `pre_filter` -> MiniMax-M2.7
  - future helper stages `discovery` / `search` -> MiniMax-M2.7
- Recommended LiteLLM alias ownership for the first rollout:
  - `vs-ai-default` -> direct DeepSeek-compatible fallback
  - `vs-ai-analysis` -> DeepSeek
  - `vs-ai-summary` -> MiniMax-M2.7
  - `vs-ai-forecast` -> DeepSeek
  - `vs-ai-prefilter` -> MiniMax-M2.7
  - `vs-ai-discovery` -> MiniMax-M2.7
  - `vs-ai-search` -> MiniMax-M2.7
- Use `D:\GitHub\auto\config\litellm\litellm-config.example.yaml` as the
  starting point for the local gateway config.

```env
ANALYSIS_AI_PROVIDER=deepseek
ANALYSIS_AI_BASE_URL=https://api.deepseek.com
ANALYSIS_AI_MODEL=deepseek-chat

SUMMARY_AI_PROVIDER=minimax_svips
SUMMARY_AI_BASE_URL=https://api.svips.org/v1
SUMMARY_AI_MODEL=MiniMax-M2.7
SUMMARY_AI_API_KEY=<your-minimax-key>

FORECAST_AI_PROVIDER=deepseek
FORECAST_AI_BASE_URL=https://api.deepseek.com
FORECAST_AI_MODEL=deepseek-chat

PREFILTER_AI_PROVIDER=minimax_svips
PREFILTER_AI_BASE_URL=https://api.svips.org/v1
PREFILTER_AI_MODEL=MiniMax-M2.7
PREFILTER_AI_API_KEY=<your-minimax-key>

DISCOVERY_AI_PROVIDER=minimax_svips
DISCOVERY_AI_BASE_URL=https://api.svips.org/v1
DISCOVERY_AI_MODEL=MiniMax-M2.7

SEARCH_AI_PROVIDER=minimax_svips
SEARCH_AI_BASE_URL=https://api.svips.org/v1
SEARCH_AI_MODEL=MiniMax-M2.7
```

LiteLLM alias example / LiteLLM 首轮 alias 示例:

```env
AI_PROVIDER=litellm_proxy
AI_BASE_URL=http://127.0.0.1:4000
AI_MODEL=vs-ai-default
LITELLM_MASTER_KEY=sk-change-me

ANALYSIS_AI_PROVIDER=litellm_proxy
ANALYSIS_AI_MODEL=vs-ai-analysis

SUMMARY_AI_PROVIDER=litellm_proxy
SUMMARY_AI_MODEL=vs-ai-summary

FORECAST_AI_PROVIDER=litellm_proxy
FORECAST_AI_MODEL=vs-ai-forecast

PREFILTER_AI_PROVIDER=litellm_proxy
PREFILTER_AI_MODEL=vs-ai-prefilter
```

GitHub / Actions note:

- Local runs can switch providers directly with `.env` or temporary env vars.
- Current GitHub workflows now support the same unified provider contract.
- Remote runs still default to DeepSeek when no repository variables are set.
- To switch the remote default provider, configure Repository Variables:
  - `AI_PROVIDER`
  - `AI_BASE_URL`
  - `AI_MODEL`
- Configure Repository Secrets:
  - `DEEPSEEK_API_KEY` for the DeepSeek-default path
  - `AI_API_KEY` for OpenAI-compatible non-DeepSeek providers
- Optional remote stage routing is also supported through Repository Variables
  and Secrets:
  - Variables: `ANALYSIS_AI_PROVIDER`, `ANALYSIS_AI_BASE_URL`,
    `ANALYSIS_AI_MODEL`, `SUMMARY_AI_PROVIDER`, `SUMMARY_AI_BASE_URL`,
    `SUMMARY_AI_MODEL`, `FORECAST_AI_PROVIDER`, `FORECAST_AI_BASE_URL`,
    `FORECAST_AI_MODEL`
  - Secrets: `ANALYSIS_AI_API_KEY`, `SUMMARY_AI_API_KEY`,
    `FORECAST_AI_API_KEY`
- Recommended first remote validation:
  - use `workflow_dispatch`
  - set `push_enabled=false`
  - record the run link / run id, then continue local work
  - only return to inspect final remote results when the user explicitly asks or a later task depends on them
- For the first LiteLLM rollout, prefer local verification first and treat the
  gateway as an optional path. Keep direct DeepSeek / MiniMax config ready as
  the rollback path.

Langfuse tracing / Langfuse tracing 首轮接入:

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENV=local
LANGFUSE_CAPTURE_CONTENT=false
```

- Verified rollout status / 已验证状态（2026-04-20）:
  - local metadata-first tracing works with Langfuse Cloud
  - GitHub Actions reusable workflows now pass through the required `LANGFUSE_*`
    environment variables
  - both `push` and manual `workflow_dispatch` runs have been verified with
    `tracing.enabled=true`
  - successful Langfuse runs now write `trace_id` and `trace_url` into
    `data/state/run-status.json`
- Remote GitHub Actions config / 远端配置:
  - Repository Variables:
    `LANGFUSE_ENABLED`, `LANGFUSE_BASE_URL`, `LANGFUSE_ENV`,
    `LANGFUSE_CAPTURE_CONTENT`
  - Repository Secrets:
    `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- First batch uses metadata-first tracing: trace metadata, stage names, provider,
  model, timing, token usage, and status are uploaded by default.
- Prompt and response bodies are not uploaded unless
  `LANGFUSE_CAPTURE_CONTENT=true`.

### 2. Run once / 本地生成一次日报

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once
```

### 3. Run reviewed mode / 生成人工复核轨

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>
```

If reviewer metadata is not ready yet, reviewed mode still works / 如果暂时没有复核人和备注，也可以先跑:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once --publication-mode reviewed
```

### 4. Sync Feishu workspace / 同步飞书协作面

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli sync-feishu-workspace --publication-mode reviewed
python -m auto_report.cli diagnose-delivery --mode full-report --send --channels feishu
```

This sidecar is local-only. It is for local verification, prettier Feishu output,
and local collaboration sync; GitHub Actions should continue to use the built-in
official Feishu API push path only.

When `FEISHU_SIDECAR_ENABLED=true`, `run-once` also updates the Feishu Doc,
governance sheet, and governance task list after report generation. When
`GITHUB_ACTIONS=true`, the sidecar is skipped automatically even if enabled.

## Verification / 发布前验证

Run from `D:\GitHub\auto`:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
$env:AUTO_PUSH_ENABLED='false'
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
```

`build-review-queue` now writes two local review artifacts:

- `out/review-queue/review-issues.json` for report-topic review candidates
- `out/review-queue/source-lead-issues.json` for governance/discovery lead review candidates
- `out/review-queue/source-lead-review-status.json` for lightweight human decisions
- `out/review-queue/candidate-updates.json` for actionable source/watch updates
- `out/source-governance/changedetection-watch-registry.json` for repo-local watch progression
- `out/source-governance/watch-run-results.json` for the latest local watch run summary
- `out/source-governance/watch-run-state.json` for local watch baselines / seen entries

Recommended local lead-review loop:

1. inspect `source-lead-issues.json`
2. update matching entries in `source-lead-review-status.json` to `approved`, `rejected`, or `deferred`
3. rerun `python -m auto_report.cli build-review-queue`
4. inspect `candidate-updates.json` and use it as the next source/watch update input set
5. run `python -m auto_report.cli apply-source-updates`
6. run `python -m auto_report.cli run-watch-checks`

Recommended current finish-up order / 当前推荐收尾顺序:

1. check `out/source-governance/watch-run-results.json`
2. clear any `blocked` watch items that are still worth keeping
3. run the full local verification chain
4. for Feishu card validation, prefer `diagnose-delivery --mode full-report --send --channels feishu`
5. only then `push` and optionally trigger remote workflow

Workflow validation profiles / workflow 校验档位:

- `daily`
  - `collect-report.yml`
  - `delivery-canary.yml`
- `recovery`
  - `backfill-report.yml`
  - `compensate-report.yml`
- `full`
  - 全量校验以上四个入口 workflow

## Publishing Surface / 发布面

Latest report outputs / 最新报告产物:

- `data/reports/latest-summary.*`
- `data/reports/latest-summary-auto.*`
- `data/reports/latest-summary-reviewed.*`

Runtime state / 运行状态:

- `data/state/run-status.json`

Public site / 公开站产物:

- `docs/index.html`
- `docs/archives/`
- `docs/weekly/`
- `docs/special/`
- `docs/feed.json`
- `docs/rss.xml`

Internal ops outputs / 内部治理产物:

- `out/ops-dashboard/index.html`
- `out/source-governance/source-governance.json`

Push channel behavior / 推送渠道策略:

- PushPlus:
  - short
  - risk-alert
- Feishu:
  - medium
  - reviewed-note
- Telegram:
  - long
  - reviewed-long

All three channels always include / 三条推送始终同时带:

- `公开阅读： https://wsysgz.github.io/VS_AI/`
- `GitHub 原文： <当前 latest-summary 对应链接>`

## Repository Layout / 仓库结构

```text
.
├─ .github/workflows/    workflow entrypoints and reusable workflows
├─ config/               providers, sources, domains, prompts, eval dataset
├─ data/                 reports, archives, runtime state
├─ docs/                 manuals and published Pages outputs
├─ scripts/              local validation helpers
├─ src/auto_report/      application source code
└─ tests/                regression and behavior tests
```

## Key Notes / 关键说明

- Local verification comes before push.
- `workflow_dispatch` always runs the pushed remote ref, not local unpushed edits.
- After a remote run is triggered, record the run id and continue local work; do
  not front-watch the run, and do not require a dedicated final-result check
  unless the next task depends on it.
- The public reading link always stays at `https://wsysgz.github.io/VS_AI/`; it does not switch to archive URLs.
- `run-status.json` is the operational source of truth for delivery, review, AI metrics, and source health.
- Report timestamps and archive dates follow the configured timezone so compensation logic can judge same-day status correctly.

