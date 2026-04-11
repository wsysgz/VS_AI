# VS_AI 用户指南

本指南帮助维护者以日常运营为中心：本地跑 pipeline、确认每日 07:00 报告、验证推送通道，并快速定位常见的操作面板。

接手优先顺序建议为：`README.md` → `docs/HANDOFF.md` → `docs/OPS_RUNBOOK.md` → 本文；如果你现在的目标是“先恢复运维能力”，先看 `OPS_RUNBOOK` 会更快。

在这台机器上建议先执行 `$env:PYTHONPATH='src'` 再跑本地 Python 命令。当前存在多个 `auto_report` worktree / 安装源时，裸跑 `python -m pytest` 或 `python -m auto_report.cli` 可能导入到错误路径。

## 每日节奏

- `Collect And Report` workflow 每天北京时间 07:00 触发综合总报，PushPlus 发送微信短摘要，Feishu 发送中长度结构化摘要，Telegram 发送完整长文报告（分别通过 `push-channels-guide` 详细说明）。
- 默认发布轨为 `auto`；如需补发人工复核版，可在本地命令或 GitHub 手动 workflow 中指定 `publication_mode=reviewed`，系统会保留 `latest-summary-auto.*` 和 `latest-summary-reviewed.*` 两套输出。
- 本地开发时先在仓库根目录准备环境、跑一遍 `run-once`，再确认 `data/reports/latest-summary.md` 与 `data/state/run-status.json` 结果，再推送 `main`。
- 无论是工作日还是排查问题，始终以 `README → USER_GUIDE → TECHNICAL_GUIDE → ARCHITECTURE → push-channels-guide` 的顺序获取上下文，避免读到过时内容。

## 环境准备

1. `python -m venv .venv`；执行 `.venv\Scripts\Activate.ps1` 后，`pip install -r requirements.txt` + `pip install -e .`。
2. 复制 `.env.example` 为 `.env`（如果已有则跳过），填写 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` / `AI_API_KEY`（按 `AI_PROVIDER` 选择）、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID`、`FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID`，更多变量详见 [Technical Guide](TECHNICAL_GUIDE.md)。
3. `python -m auto_report.cli run-once` 触发一次完整流程。若要生成人工复核版，可用 `python -m auto_report.cli run-once --publication-mode reviewed`。首次运行前建议先跑 `$env:PYTHONPATH='src'; python -m pytest tests -q` 确保基础功能正常。

## 常用命令

| 命令 | 用途 | 何时使用 |
|------|------|----------|
| `python -m auto_report.cli run-once [--publication-mode reviewed]` | 全流程采集→分析→渲染→推送 | 本地验证、部署前检查、人工复核版重发 |
| `python -m auto_report.cli diagnose-delivery --mode canary` | 检查三端配置，不实际发送 | 首次对接、排查 secrets / `.env` |
| `python -m auto_report.cli diagnose-delivery --mode canary --send` | 向三端发送一条 canary 诊断消息 | 上线前验收、怀疑某个通道失联时 |
| `python -m auto_report.cli diagnose-delivery --mode full-report --send` | 用各渠道生产模板做实发验证 | 怀疑正文格式、分段或模板异常时 |
| `python -m auto_report.cli collect-only` | 只采集 + 预处理 | 调试数据源或减少 AI 调用 |
| `python -m auto_report.cli analyze-only` | 用已有中间数据跑 AI | 跟踪分析错误、重跑 AI |
| `python -m auto_report.cli render-report [--publication-mode reviewed]` | 全流程采集→分析→渲染，但不推送 | 检查模板、重建 auto/reviewed 报告但不发通知 |
| `python -m auto_report.cli build-pages` | 重建公开站 `docs/index.html`、`docs/archives/`、`docs/weekly/`、`docs/special/`、`docs/search-index.json`、`docs/feed.json`、`docs/rss.xml` | 验证 Pages 站点、周报页与专题页生成逻辑 |
| `python -m auto_report.cli build-ops-dashboard` | 生成私有运营视图到 `out/ops-dashboard/index.html` | 检查送达/调度/阶段状态，以及最近 prompt-eval 趋势与回归降分，不公开发布 |
| `python -m auto_report.cli build-review-queue` | 从 `latest-summary.json` 生成人工复核 issue payload 到 `out/review-queue/review-issues.json` | 准备高价值主题的 GitHub Issue 复核入口 |
| `python -m auto_report.cli evaluate-prompts --dataset <path>` | 运行离线 Prompt/Eval，对比 prompt/version/model/metrics 组合 | 做本地 prompt 回归、比较不同版本输出质量 |
| `python -m auto_report.cli backfill --target-date YYYY-MM-DD [--publication-mode reviewed]` | 补报单日历史日期并刷新 Pages 输出 | 手动修补某天缺报，或补发 reviewed 版本 |

## 本地快验顺序

1. `pwsh ./scripts/check-workflows.ps1`：执行 workflow guard，覆盖 `actionlint`、`act` 与本地 workflow 校验脚本。
2. `$env:PYTHONPATH='src'; python -m pytest tests -q`：确认 Python 主流程、workflow 契约、PromptOps 与 intelligence 相关测试通过。
3. `$env:PYTHONPATH='src'; python -m auto_report.cli build-ops-dashboard`：检查私有 dashboard 是否能读到最新 `run-status.json` 与 `out/evals/`。
4. 需要准备人工复核议题时执行 `$env:PYTHONPATH='src'; python -m auto_report.cli build-review-queue`。
5. 需要做 prompt 回归时再执行 `$env:PYTHONPATH='src'; python -m auto_report.cli evaluate-prompts --dataset <path>`。

## 验证输出

- 查看 `data/reports/latest-summary.md` 与 `data/reports/latest-summary.html` 确认内容；双轨发布时还要同时检查 `data/reports/latest-summary-auto.*`、`data/reports/latest-summary-reviewed.*`。`data/state/run-status.json` 记录 `generated_files`、`publication_mode`、`timings`、`stage_status`、`delivery_results`、`scheduler` 与 `external_enrichment`。
- `build-pages` 之后可直接检查 `docs/weekly/index.html` 与 `docs/weekly/<year-week>/index.html`，确认周报页是否按 ISO 周正确聚合。
- 专题页当前默认输出到 `docs/special/`，可直接检查 `docs/special/index.html`、`docs/special/verified/index.html`、`docs/special/risk-watch/index.html`。
- 离线 Prompt/Eval 结果默认写到 `out/evals/`，可直接比对不同 `prompt_id` / `version` / `model` 的 `overall_score_avg`、`required_fields_score_avg`、`keyword_recall_avg`。
- 私有 ops dashboard 会合并展示 `run-status.json` 与最近的 `out/evals/prompt-eval-*.json`，方便快速判断“哪次 prompt 更新开始降分”。
- 当启用外部补证时，私有 ops dashboard 还会展示 `attempted / succeeded / failed / skipped / success_rate / circuit`，用于判断 enrichment 是否命中或已经熔断。
- 人工复核队列默认写到 `out/review-queue/review-issues.json`；每条记录都已带 title/body/labels，可直接交给后续 workflow 或手工建 issue。
- `Collect And Report` workflow 现在会自动构建并消费 review queue，对符合条件的高价值主题创建 `[V7 review]` issue。
- 如果本地跑出错误，先检查 `logs/`（可通过 `auto_report.cli` 添加日志）以及 `data/state/run-status.json` 的最后一次 `stage` 记录，再根据 `push-channels-guide` 验证各通知通道。
- 如只想确认推送配置是否就绪，不必每次都跑完整 pipeline，可先执行 `python -m auto_report.cli diagnose-delivery --mode canary`。
- 运行完毕后再 `git status` 查看 `data/` 变化是否按 CI 预期被忽略，确保本地临时输出未误提交。

## 仓库对接

1. 在 GitHub 仓库中确认 `Actions > General > Workflow permissions` 为 `Read and write permissions`，否则自动回写报表和 Pages 会失败。
2. 在 GitHub Secrets 中补齐 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。
3. 手动触发 `Collect And Report` 时，如果需要真实推送，把 workflow input `push_enabled` 设为 `true`；如果需要人工复核轨，同时把 `publication_mode` 设为 `reviewed`。
4. 手动触发 `Backfill Report` 时，workflow 会先执行 `backfill`，再执行 `build-pages` 与 `build-ops-dashboard`；同样可以把 `publication_mode` 设为 `reviewed`。自动提交范围保持为 `data/**`、`docs/index.html`、`docs/archives/`、`docs/.nojekyll`，私有 ops dashboard 只进 artifact 不公开。
5. 远端验证优先看 `data/state/run-status.json` 中的 `delivery_results.successful_channels`，不要只看 workflow 页面是否是绿色。
6. 当前远端 reliability issue 会覆盖三类场景：`all delivery channels failed`、`consecutive canary failures`、`high risk report detected`。
7. 本地默认仍关闭外部补证；如需手动启用，可在运行前设置 `EXTERNAL_ENRICHMENT_ENABLED=true`。CI / 主 workflow 已默认开启，并限流为前 `2` 个高价值主题、单请求超时 `8` 秒。

## 失败与回滚

- 如果某个阶段（采集、AI、渲染、推送）失败，先定位对应子命令（collect/analysis/render），捕获异常和 `run-status` 中的 `error` 信息。
- 某些失败源于配置问题（如缺少 `DEEPSEEK_API_KEY`、Telegram token、Feishu secrets，或 PushPlus secret 签名错误），请参考 `docs/TECHNICAL_GUIDE.md` 和 `docs/push-channels-guide.md`，修复 `.env` 或 Secrets。
- 需要回滚数据时，可 `git checkout -- data/reports data/state`（谨慎操作），因为 `data/` 在流水线中由 CI 自动归档，不应在本地提交。

## AI Key 缺失时的降级行为

无 `DEEPSEEK_API_KEY` 时，系统自动启用规则摘要（rule summary）模式，只保留结构化的标题、链接、来源和手工编写的规则评论。虽然 AI 分析与总结被跳过，但全流程仍然可以生成报告、推送多通道，便于快速恢复。

## 参考

- 详细 AI/环境配置与降级行为：`docs/TECHNICAL_GUIDE.md`。
- 系统结构分析与数据流：`docs/ARCHITECTURE.md`。
- 推送通道配置与验证：`docs/push-channels-guide.md`。
