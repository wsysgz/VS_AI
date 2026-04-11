# VS_AI 架构视图

本节从系统组件与数据流角度概述 VS_AI：如何从多个数据源采集信息、通过 AI 生成洞察、再渲染并推送到多通道，同时把运维状态、PromptOps、review queue 与公开阅读站一起收口。

## 1. 总体流程

```
collect → dedup/score → topic builder → AI pipeline (analysis → summary → forecast)
        → intelligence layer (memory / lifecycle / risk / enrichment)
        → render → publish(auto / reviewed) → push → archive
        → pages / ops dashboard / review queue
```

- `collect_all_items()`（`sources/collector.py`）并发抓取 RSS、GitHub、Hacker News、网站列表页。
- `build_report_package()`（`pipeline/analysis.py`）负责去重、评分、主题聚合，并在 `pipeline/intelligence.py` 中补齐跨日记忆、生命周期、风险等级、当前轮 support evidence 与外部 enrichment。
- `render_reports()`（`app.py` + `outputs/`）渲染 Markdown / HTML / JSON，并同步准备 `data/reports`、`data/state`、`data/archives`。
- 推送阶段调用 `integrations/pushplus.py`、`integrations/telegram.py`、`integrations/feishu.py`，由 `run_once()` 统一汇总送达状态。
- 运营侧附属产物包括：
  - `build-pages`：公开 Pages 阅读站
  - `build-ops-dashboard`：私有 ops dashboard
  - `build-review-queue`：高价值主题人工复核 issue payload
  - `evaluate-prompts --dataset ...`：离线 Prompt/Eval 回归
- CLI 命令集中注册在 `cli.py`，继续作为唯一入口，不引入第二套工具链。

## 2. 关键模块

- `src/auto_report/app.py`：核心编排，包含 `StageTimer`、`run_once()`、`run_backfill()`，并负责解析 `publication_mode`、写入双轨输出、构造 track 专属详情链接。
- `src/auto_report/settings.py`：将 `.env` 变量封装进 `Settings` dataclass，供 pipeline 与 integrations 共享。
- `src/auto_report/pipeline/analysis.py`：主 package builder，衔接 dedup/scoring、AI pipeline 与 intelligence layer。
- `src/auto_report/pipeline/intelligence.py`：跨日主线记忆、`new/rising/verified/fading` 生命周期、`risk_level`、support evidence、外部 enrichment、单次运行熔断与 enrichment 可观测性。
- `src/auto_report/pipeline/review_queue.py`：从最新报告中提取高价值主题，生成 GitHub Issue 复核 payload。
- `src/auto_report/pipeline/prompt_loader.py`：版本化 prompt registry，并兼容 legacy `config/ai_reading/*.md`。
- `src/auto_report/pipeline/prompt_evaluator.py`：离线 Prompt/Eval 回归，输出到 `out/evals/`。
- `src/auto_report/pipeline/ai_pipeline.py`：analysis / summary / forecast 三阶段 AI 编排。
- `src/auto_report/pipeline/dedup.py`、`scoring.py`、`topic_builder.py`：主题去重、打分、候选主题构建。
- `src/auto_report/sources/`：各类数据源（RSS、GitHub、HN、websites），抽象复用 `collector.py`。
- `src/auto_report/integrations/`：统一 LLM 客户端 + 通道适配器，保持 AI 与推送低耦合。
- `src/auto_report/outputs/renderers.py`：日报 Markdown / HTML / JSON 与多通道推送文本模板，当前已拆为 PushPlus `short`、Feishu `medium`、Telegram `long` 三档。
- `src/auto_report/outputs/pages_builder.py`：公开 Pages 站点生成器，当前已覆盖首页、archives、weekly、special、search index、JSON Feed、RSS，并在同日存在两条轨时优先选择 reviewed。
- `src/auto_report/outputs/ops_dashboard.py`：私有 dashboard，聚合 `run-status.json` 与 prompt-eval 历史，并展示 external enrichment 运行指标。
- `src/auto_report/workflow_guard.py`：workflow 本地快验逻辑，供 `scripts/check-workflows.ps1` 和 CI 复用。
- `src/auto_report/domains/`、`models/`：定义领域、数据模型、TopicCandidate 与 CollectedItem，便于后续扩展。

## 3. 数据存放

- `data/reports/`：最新报告（兼容用 `latest-summary.*` + 双轨 `latest-summary-auto.*` / `latest-summary-reviewed.*`），由 `render_reports()` 写入。
- `data/state/`：`run-status.json`、`dedup-index.json`、中间态文件等，用于后续回放、CI 检查与运维排障。
- `data/archives/`：按日期归档的历史结果；当前既保留兼容命名，也保留 `*-summary-auto.*` / `*-summary-reviewed.*` 的轨道化归档文件，GitHub Actions 会自动提交到 `main`，避免触发 `push`。
- `docs/archives/`：公开日报归档页。
- `docs/weekly/`：公开周报聚合页。
- `docs/special/`：公开专题聚合页，当前包含 `verified` 与 `risk-watch` 两类专题。
- `docs/search-index.json`、`docs/feed.json`、`docs/rss.xml`：公开检索与订阅面。
- `out/ops-dashboard/`：私有 dashboard，不发布到 Pages。
- `out/evals/`：离线 Prompt/Eval 历史结果。
- `out/review-queue/`：人工复核 issue payload。
- `config/`：数据源、领域、prompt registry 与 legacy prompt 文件。

## 4. 定时与监控

- 每次运行在 `StageTimer` 中打点，`run-status.json` 当前覆盖：
  - `timings`
  - `generated_files`
  - `stage_status`
  - `delivery_results`
  - `scheduler`
  - `risk_level`
  - `external_enrichment`
- `data/state/run-status.json` 也是 `tests/test_observability.py` 关注的关键文件，确认 `StageTimer` 与 `_to_relative_paths()` 的行为一致。
- `run-status.json` 当前还会显式记录 `publication_mode`，便于运维判断当前是自动轨还是人工复核轨。
- private ops dashboard 直接消费 `run-status.json`，并叠加最近的 prompt-eval 历史；external enrichment 的 `attempted / succeeded / failed / skipped / success_rate / circuit` 也在这里观察。
- CI workflow 现已收口为 reusable workflow 体系，主入口仍是 `collect-report.yml`，并补有：
  - `delivery-canary.yml`
  - `compensate-report.yml`
  - `reusable-pages.yml`
  - `reusable-ops-dashboard.yml`
  - `reusable-review-queue.yml`
  - `reusable-python-test.yml`
  - `reusable-workflow-guard.yml`

## 5. 拓展点与可观察性

- `docs/upgrade-plan/` 提供了 V6/V7 的升级背景与对齐资料，可在需要扩展（如 MCP、邮件、双语）时作为参考入口。
- `docs/superpowers/` 下的历史状态记录帮助追踪每次 handoff、stage 的进行状态。
- 当前尚未完成的主要面向包括：
  - Topic 专题页继续深化，而不只停在分类聚合页
  - 渠道模板层继续深化成更丰富的 per-channel 变体，而不只是当前的 `short / medium / long`
  - enrichment 的跨日命中率和 source budget 进一步硬化
  - reviewed 轨后续可再补 reviewer metadata / 审核备注，而不仅是当前的轨道切换与 public preference
- 任何新增模块应先保证 `StageTimer`、`run-status.json` 和私有 ops dashboard 仍然能追踪到。
