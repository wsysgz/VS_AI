# VS_AI 架构视图

本节从系统组件与数据流角度概述 VS_AI：如何从多个数据源采集信息、通过 AI 生成洞察、再渲染并推送到多通道。

## 1. 总体流程

```
collect → dedup/score → topic builder → AI pipeline (analysis → summary → forecast) → render → push → archive
```

- `collect_all_items()`（`pipeline/collector.py`）并发抓取 RSS、GitHub、Hacker News、网站列表页。
- `build_report_package()`（`pipeline/analysis.py`）负责去重、评分、主题聚合，并在 `integrations/llm_client.py` 驱动下调用 AI。
- `render_reports()`（`pipeline/run_once.py` + `outputs/`）渲染 MD/HTML/JSON 并准备 `data/reports` 与 `data/state`。
- 推送阶段调用 `integrations/pushplus.py`、`integrations/telegram.py`、`integrations/feishu.py`，最终由 GitHub Actions 步骤 `render-and-push` 触发。
- 每个 CLI 命令（`run-once`、`collect-only`、`analyze-only`、`render-report`、`backfill`）在 `cli.py` 中注册，便于调试与 CI job 划分。

## 2. 关键模块

- `src/auto_report/app.py`：核心编排，包含 `StageTimer`（每个 stage 计时、写入 `run-status.json`）、`run_once()` 和 `run_backfill()`。
- `src/auto_report/settings.py`：将 `.env` 变量封装进 `Settings` dataclass，供 pipeline 与 integrations 共享。
- `src/auto_report/pipeline/`：包含 `analysis.py`（summary 构建）、`ai_pipeline.py`（三阶段 AI）、`dedup.py`、`scoring.py`、`topic_builder.py`、`prompt_loader.py`。
- `src/auto_report/sources/`：各类数据源（RSS、GitHub、HN、websites），抽象复用 `collector.py`。
- `src/auto_report/integrations/`：统一 LLM 客户端 + 通道适配器，保持 AI 与推送低耦合。
- `src/auto_report/outputs/`：`renderers.py` 负责 MD/HTML/JSON 模板，`archive.py` 负责归档写入。
- `src/auto_report/domains/`、`models/`：定义领域、数据模型、TopicCandidate 与 CollectedItem，便于后续扩展。

## 3. 数据存放

- `data/reports/`：最新报告（`latest-summary.md`、`.json`、`.html`），由 `render_reports()` 写入。
- `data/state/`：`run-status.json`、`dedup-index.json` 等，用于后续回放与 CI 检察。
- `data/archives/`：按日期归档的历史结果，GitHub Actions 会自动提交到 `main`，避免触发 `push`。
- `docs/archives/`：Pages 用的 HTML 报告快照，不影响核心 pipeline。
- `config/`：所有数据源、领域、AI prompt（`config/ai_reading/*.md`）。

## 4. 定时与监控

- 每次运行在 `StageTimer` 中打点，`run-status.json` 含 `timings`、`generated_files` 与推送结果（status/pushes）。
- `data/state/run-status.json` 也是 `tests/test_observability.py` 关注的关键文件，确认 `StageTimer` 与 `_to_relative_paths()` 的行为一致。
- CI workflow（`collect-report.yml`）分为 five job（test → collect → analyze → render/push → deploy-pages），每一步使用已有 artifacts 串联。

## 5. 拓展点与可观察性

- `docs/upgrade-plan/` 提供了 V6/V7 的升级背景与对齐资料，可在需要扩展（如 MCP、邮件、双语）时作为参考入口。
- `docs/superpowers/` 下的历史状态记录帮助追踪每次 handoff、stage 的进行状态。
- 任何新增模块应先保证 `StageTimer` 和 `run-status` 仍然能追踪到。
