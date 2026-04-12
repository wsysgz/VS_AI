# VS_AI

VS_AI is a daily AI intelligence workflow for collecting signals, generating structured analysis, publishing reports, and updating a public reading site.

VS_AI 是一个面向每日 AI 情报生产的自动化工程，负责采集多源信号、生成结构化分析、推送多渠道报告，并持续更新公开阅读站。

Public site / 公开站点:
`https://wsysgz.github.io/VS_AI/`

## Overview / 项目概览

- Focus:
  - AI / LLM / Agent
  - AI × Electronics
- Daily output:
  - structured report
  - public Pages site
  - PushPlus short summary
  - Feishu medium summary
  - Telegram full report
- Publishing rule:
  - every push message includes the public site link
  - every push message includes the current GitHub raw report link
  - `auto` and `reviewed` modes are both supported

## Capabilities / 核心能力

- Multi-source collection from RSS, GitHub, Hacker News, and curated websites.
- Topic deduplication, scoring, clustering, analysis, summary, and forecast generation.
- Dual-track publishing with `auto` and `reviewed` outputs.
- Public Pages generation with archive, weekly, special, feed, and RSS outputs.
- Delivery observability through `run-status.json`, review queue, and ops dashboard artifacts.
- Workflow validation with fixed local profiles: `daily`, `recovery`, `full`.

## Repository Layout / 目录结构

```text
.
├─ .github/workflows/    GitHub Actions workflows
├─ config/               sources, providers, prompts, evaluation dataset
├─ data/                 reports, archives, state
├─ docs/                 manuals + published Pages outputs
├─ scripts/              bootstrap and workflow validation scripts
├─ src/auto_report/      application source code
└─ tests/                test suite
```

## Quick Start / 快速开始

```powershell
cd D:\GitHub\auto
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```

Fill `.env` with the keys you need:

- `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` / `AI_API_KEY`
- `PUSHPLUS_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_CHAT_ID`

Then run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once
```

If you need a reviewed publication:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>
```

## Verification / 验证基线

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
```

Current baseline: `191 passed`

## Manuals / 手册入口

- [docs/USER_GUIDE.md](docs/USER_GUIDE.md)
  - Daily usage guide for local runs, report viewing, reviewed output, page rebuilds, and common tasks.
- [docs/OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md)
  - Operations runbook for validation, GitHub Actions, incident triage, and production acceptance.
- [docs/HANDOFF.md](docs/HANDOFF.md)
  - Technical handoff guide covering architecture, module responsibilities, configuration model, and extension points.
- [AGENTS.md](AGENTS.md)
  - Project-local agent instructions and engineering guardrails.

## Outputs / 主要产物

- Latest reports:
  - `data/reports/latest-summary.*`
  - `data/reports/latest-summary-auto.*`
  - `data/reports/latest-summary-reviewed.*`
- Runtime state:
  - `data/state/run-status.json`
- Public site:
  - `docs/index.html`
  - `docs/archives/`
  - `docs/weekly/`
  - `docs/special/`
  - `docs/feed.json`
  - `docs/rss.xml`

## Notes / 说明

- Local verification should always happen before pushing to GitHub.
- `workflow_dispatch` on GitHub always runs the pushed remote ref, not your local unpushed changes.
- The public site entry is always `https://wsysgz.github.io/VS_AI/`; notifications do not switch to archive URLs.
