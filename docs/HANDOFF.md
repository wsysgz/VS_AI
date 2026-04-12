# VS_AI 技术交接手册

> 最后更新：2026-04-12

这份手册面向新维护者和后续开发者。

目标不是教你“怎么点按钮”，而是让你在较短时间内建立对项目结构、数据流、配置模型和扩展边界的整体认知，从而可以稳定接手、修改和继续演进。

## 1. 建议接手顺序

1. `README.md`
2. 本手册
3. `docs/OPS_RUNBOOK.md`
4. `docs/USER_GUIDE.md`
5. `AGENTS.md`

## 2. 项目定位

VS_AI 是一个“日报生产工程”，不是单纯的抓取脚本。

它的主目标是：

- 从多源采集 AI 相关信号
- 聚合成主题
- 生成分析、总结、预测
- 渲染成报告
- 推送到多渠道
- 同步更新公开 Pages 站点

当前覆盖两个核心领域：

- AI / LLM / Agent
- AI × Electronics

## 3. 总体数据流

主链路可以概括为：

```text
collect
→ dedup / score
→ topic builder
→ AI pipeline (analysis / summary / forecast)
→ intelligence layer
→ render
→ publish (auto / reviewed)
→ push
→ archive
→ pages / review queue / ops dashboard
```

可以把它理解成四层：

1. 输入层
   - RSS、GitHub、Hacker News、网站列表页
2. 分析层
   - 去重、评分、聚类、主题构建、AI 生成
3. 发布层
   - Markdown / HTML / JSON 报告
   - PushPlus / Feishu / Telegram 模板
4. 运营层
   - Pages
   - run-status
   - review queue
   - ops dashboard

## 4. 关键目录与职责

### 源码

- `src/auto_report/app.py`
  - 主编排入口
  - 负责运行流程、发布轨控制、结果写入
- `src/auto_report/cli.py`
  - 全部命令入口
- `src/auto_report/settings.py`
  - 环境变量与配置封装

### Pipeline

- `src/auto_report/pipeline/analysis.py`
  - 主分析收口
- `src/auto_report/pipeline/ai_pipeline.py`
  - analysis / summary / forecast 三阶段 AI 编排
- `src/auto_report/pipeline/intelligence.py`
  - 生命周期、主线记忆、风险、补证观测
- `src/auto_report/pipeline/topic_builder.py`
  - 主题构建
- `src/auto_report/pipeline/dedup.py`
  - 去重
- `src/auto_report/pipeline/scoring.py`
  - 评分逻辑
- `src/auto_report/pipeline/prompt_loader.py`
  - prompt registry 装载
- `src/auto_report/pipeline/prompt_evaluator.py`
  - 离线 Prompt/Eval
- `src/auto_report/pipeline/review_queue.py`
  - 高价值主题复核队列

### 数据源

- `src/auto_report/sources/collector.py`
  - 汇总所有来源
- `src/auto_report/sources/rss.py`
- `src/auto_report/sources/github.py`
- `src/auto_report/sources/hn.py`
- `src/auto_report/sources/websites.py`

### 集成层

- `src/auto_report/integrations/llm_client.py`
  - 统一 LLM 客户端
- `src/auto_report/integrations/pushplus.py`
- `src/auto_report/integrations/telegram.py`
- `src/auto_report/integrations/feishu.py`

### 输出层

- `src/auto_report/outputs/renderers.py`
  - 报告和渠道消息模板
- `src/auto_report/outputs/pages_builder.py`
  - Pages 站点构建
- `src/auto_report/outputs/ops_dashboard.py`
  - 私有运维看板
- `src/auto_report/outputs/archive.py`
  - 归档输出

## 5. 关键配置模型

### 基础配置

- `.env.example`
  - 环境变量样例
- `config/providers.yaml`
  - provider 配置
- `config/sources/*.yaml`
  - 数据源配置
- `config/domains/*.yaml`
  - 领域配置
- `config/schedules.yaml`
  - 调度配置

### PromptOps

- `config/ai_reading/registry.json`
  - 正式 prompt registry
- `config/ai_reading/*.md`
  - 现有 prompt 文本资产
- `config/prompt_eval/baseline-v1.json`
  - 正式 benchmark dataset

### 两个重要运行模式

- `publication_mode=auto`
  - 默认自动发布轨
- `publication_mode=reviewed`
  - 人工复核发布轨

当 `publication_mode=reviewed` 时，系统会额外处理：

- `reviewer`
- `review_note`
- `latest-summary-reviewed.*`
- 通知标题中的 reviewed 标识
- Pages 上对 reviewed 的优先展示

## 6. 最重要的状态文件

### `data/state/run-status.json`

这是最关键的运行状态文件。

必看字段：

- `publication_mode`
- `review`
- `delivery_results`
- `risk_level`
- `stage_status`
- `ai_metrics`
- `source_health`
- `source_stats.report_topics`
- `external_enrichment`
- `timings`

这些字段分别回答：

- 当前发的是哪条轨
- 有没有人工复核信息
- 哪些通道发成功了
- 本轮风险高不高
- 哪个阶段出错了
- AI 用了什么 provider / model / token
- 来源健康是否异常
- 最终入报主题有多少
- 外部补证是否命中
- 每个阶段耗时多少

## 7. 报告与页面产物

### 报告

- `data/reports/latest-summary.*`
- `data/reports/latest-summary-auto.*`
- `data/reports/latest-summary-reviewed.*`
- `data/archives/YYYY-MM-DD/`

### 页面

- `docs/index.html`
- `docs/archives/`
- `docs/weekly/`
- `docs/special/`
- `docs/feed.json`
- `docs/rss.xml`
- `docs/search-index.json`

### 私有运营产物

- `out/ops-dashboard/`
- `out/review-queue/`
- `out/evals/`

这些 `out/` 产物不属于正式仓库交付面，按需重建即可。

## 8. Workflow 拓扑

当前主入口是：

- `.github/workflows/collect-report.yml`

它会串起：

- workflow guard
- Python tests
- collect
- analyze
- report
- pages
- ops dashboard
- review queue

其他关键 workflow：

- `backfill-report.yml`
  - 指定日期补报
- `compensate-report.yml`
  - 主流程失败后的补偿
- `delivery-canary.yml`
  - 通道健康检查

### 一个关键经验

GitHub Actions 的 `workflow_dispatch` 始终执行远端已推送版本。

所以：

- 本地改完 workflow
- 必须先 push
- 再触发线上验收

## 9. 已完成的工程收口

当前你可以默认这些能力已经稳定存在：

- workflow profiles：
  - `daily`
  - `recovery`
  - `full`
- 双轨发布：
  - `auto`
  - `reviewed`
- 三通道双链接推送：
  - 公开站入口
  - GitHub 原文入口
- `run-status.json` 新字段：
  - `ai_metrics`
  - `source_health`
  - `review`
  - `source_stats.report_topics`
- Pages 周报和专题页：
  - `weekly`
  - `special`
  - `verified`
  - `emerging`
  - `risk-watch`
- review queue 自动 issue 链路

## 10. 后续扩展怎么做

### 新增数据源

通常要同时改三处：

1. `config/sources/*.yaml`
2. `src/auto_report/sources/*.py`
3. 对应测试

### 新增推送通道

通常要同时改四处：

1. `src/auto_report/integrations/`
2. `src/auto_report/outputs/renderers.py`
3. `src/auto_report/app.py`
4. 对应测试

### 修改 Prompt / Eval

通常要同时改：

1. `config/ai_reading/registry.json`
2. `config/ai_reading/*.md`
3. `config/prompt_eval/baseline-v1.json`
4. `tests/test_prompt_*`

### 修改页面结构

通常要看：

1. `src/auto_report/outputs/pages_builder.py`
2. `tests/test_pages_builder.py`
3. 生成后的 `docs/`

## 11. 接手第一小时建议

第一小时只做四件事：

1. 跑一次 `pwsh ./scripts/check-workflows.ps1 -Profile full`
2. 跑一次 `python -m pytest tests -q`
3. 跑一次 `python -m auto_report.cli run-once --publication-mode reviewed`
4. 打开 `data/state/run-status.json`

如果这四步都通了，你对项目的理解和可控度会提升得很快。

## 12. 最后提醒

- 这是一个“工程化发布系统”，不是一次性脚本集合
- 页面、推送、状态文件三者必须一起看
- 本地、远端、公开站三端要分清
- 出问题时优先相信 `run-status.json`
