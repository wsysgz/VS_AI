# VS_AI

VS_AI 是一个工程化的 AI 情报生产系统，负责采集多源信号、聚类与分析主题、生成日报、通过飞书交付，并维护公开阅读站。

公开站入口：`https://wsysgz.github.io/VS_AI/`

## 当前状态

- 工作区：`D:\GitHub\auto`
- 远端：`git@github.com:wsysgz/VS_AI.git`
- 默认分支：`main`
- 当前测试基线：`364 passed`
- V1 收口状态：公开站 IA V2、来源治理尾项、飞书单通道交付、发布链验证均已完成
- 最新完整远端发布确认：`Collect And Report` run `25049217360` success
- 最新自动产物提交：`3d87ff65 chore: update auto reports [skip ci]`

## 系统能力

- 采集来源：RSS、GitHub、Hacker News、官方网站 listing / API / sitemap
- 主链路：`collect -> dedup -> topic build -> AI analysis -> render -> publish`
- 输出面：Markdown / HTML / JSON 报告、GitHub Pages、飞书消息、review queue
- 运行态真相：`data/state/run-status.json`
- 公开交付入口：`docs/`

## 文档入口

- [工程手册.md](工程手册.md)
  - 唯一操作总手册，承接历史接手/操作文档
- [交接备忘录.md](交接备忘录.md)
  - 只保留当前状态、关键决策、最短恢复流程
- [V2升级方案.md](V2升级方案.md)
  - V2 路线图，承接 V1 的长期项与第二阶段升级
- [AGENTS.md](AGENTS.md)
  - 代理协作约束、验证流程、仓库事实

## 快速开始

```powershell
cd D:\GitHub\auto
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
$env:PYTHONPATH = "src"
```

最常用环境变量：

- AI：`AI_PROVIDER`、`AI_BASE_URL`、`AI_MODEL`、`DEEPSEEK_API_KEY`、`AI_API_KEY`
- Tracing：`LANGFUSE_ENABLED`、`LANGFUSE_PUBLIC_KEY`、`LANGFUSE_SECRET_KEY`
- Delivery：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`
- Runtime：`AUTO_PUSH_ENABLED`、`AI_DISABLE_LLM`

推荐 provider 模板：

```powershell
# DeepSeek 官方
$env:AI_PROVIDER = "deepseek"
$env:AI_BASE_URL = "https://api.deepseek.com"
$env:AI_MODEL = "deepseek-v4-flash"

# MiniMax-M2.7（OpenAI-compatible）
$env:AI_PROVIDER = "minimax_svips"
$env:AI_BASE_URL = "https://api.svips.org/v1"
$env:AI_MODEL = "MiniMax-M2.7"

# LiteLLM Gateway（本地可选）
$env:AI_PROVIDER = "litellm_proxy"
$env:AI_BASE_URL = "http://127.0.0.1:4000"
$env:AI_MODEL = "vs-ai-default"
```

## 最常用命令

```powershell
# 本地日报
python -m auto_report.cli run-once

# reviewed 轨
python -m auto_report.cli run-once --publication-mode reviewed

# 重建交付面
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue

# 本地发布前验证
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
```

## 发布规则

- 本地优先，GitHub Actions 只做阶段完成或发布级确认
- `workflow_dispatch` 只运行远端已 push 代码
- 飞书是唯一继续维护的交付通道
- 推送前至少确认本次改动对应的本地验证已通过

标准发布前链路：

```powershell
$env:PYTHONPATH = "src"
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
$env:AI_DISABLE_LLM = "true"
$env:AUTO_PUSH_ENABLED = "false"
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
```

## 仓库结构

- `src/auto_report/`：主代码
- `tests/`：测试
- `config/`：来源、provider、prompt eval 配置
- `data/`：已提交的报告、归档、运行态
- `docs/`：公开站 Pages 输出
- `scripts/`：本地辅助脚本
- `docs/superpowers/`：仅保留最近一次历史 plan/spec

## 关键事实

- `data/state/run-status.json` 是唯一运行态真相源
- `out/`、`output/`、`.pytest_*`、`.codex_*` 等目录都视为可重建运行副产物
- `renesas-blog` 当前决策是保留官方 sitemap + `curl` 证据链，不再回到 requests-only 修复路线
- V1 已退休；后续升级统一写入 `V2升级方案.md`
