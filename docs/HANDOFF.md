# VS_AI 接手手册

> **最后更新**: 2026-04-12
> **目标**: 为每天北京时间 07:00 的综合报道提供一个清晰的路径图，确保接手者可以迅速恢复系统运行。

## 接手入口

1. `README.md`
2. `docs/OPS_RUNBOOK.md`
3. `docs/USER_GUIDE.md`
4. `docs/TECHNICAL_GUIDE.md`
5. `docs/ARCHITECTURE.md`
6. `docs/push-channels-guide.md`

## 一句话分工

- `docs/OPS_RUNBOOK.md`：接手时直接照着执行的运维 runbook，包含命令入口、产物位置、workflow 对应和失败排查顺序。
- `docs/USER_GUIDE.md`：更完整的本地命令、验证动作和常规操作说明。
- `docs/TECHNICAL_GUIDE.md`：环境变量、AI provider、降级行为与配置边界。
- `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`：V7 当前真实进度，不要只看计划原文。

## 审计资料

- `docs/superpowers/`
- `docs/upgrade-plan/`
- `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`

## 维护流程（执行顺序）

- 阅读 `AGENTS.md` 以掌握快速查阅要点（认证、验证顺序、主要脚本）。
- 接手执行时优先打开 `docs/OPS_RUNBOOK.md`，它是当前最完整的运维接手页。
- 在这台机器的多 worktree / 多安装源环境里，建议先执行 `$env:PYTHONPATH='src'` 再跑本地 Python 命令，避免导入到错误的 `auto_report` 路径。
- 按照 README 和 USER_GUIDE 的指引设置 `.venv`、依赖、`.env`（关键变量包含 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`FEISHU_*`，更多详情在 Technical Guide）。
- 如需对齐当前 V7 真正完成度，先读 `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`，不要只看升级计划原文。
- 先运行 `$env:PYTHONPATH='src'; python -m auto_report.cli diagnose-delivery --mode canary` 检查三端配置，再执行 `$env:PYTHONPATH='src'; python -m auto_report.cli run-once`，检查 `data/reports/latest-summary.md`、`data/state/run-status.json` 是否包含期望输出。
- 若要产出人工复核版，可直接运行 `$env:PYTHONPATH='src'; python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>`，或在 GitHub 手动触发 workflow / backfill 时把 `publication_mode` 设为 `reviewed` 并可选填写 `reviewer` / `review_note`；系统会同时保留 `latest-summary-auto.*` 与 `latest-summary-reviewed.*`，而公开 Pages 会优先展示 reviewed。
- 注意：`run-once` 不会自动刷新 `docs/`。如果你要检查公开页是否反映了刚刚的本地结果，紧接着执行 `python -m auto_report.cli build-pages`。
- 确保每日 07:00 的自动推送按计划执行：`Collect And Report` workflow 的 `schedule` 触发会调用 PushPlus（短摘要）、Feishu（中长度结构化摘要）和 Telegram（完整长文），三端正文都会同时附带公开站入口 `https://wsysgz.github.io/VS_AI/` 与当前 GitHub 原文链接，详见 push-channels guide。
- 如需手动补报，优先使用 `Backfill Report` workflow 或 `python -m auto_report.cli backfill --target-date YYYY-MM-DD`；当前补报链路会同步重建公开 Pages 站点（`docs/index.html`、`docs/archives/`、`docs/weekly/`、`docs/special/`、`docs/search-index.json`、`docs/feed.json`、`docs/rss.xml`），并把私有 ops dashboard 作为 artifact 输出。
- `build-pages` 现在还会同步生成 `docs/weekly/` 与 `docs/special/`，接手时可以顺手检查周报页与专题页是否覆盖到最近数据。
- GitHub 手动 workflow 只会执行“已经推送到目标分支”的版本；如果本地刚修完 workflow 或 pipeline，线上复跑前必须先推送该分支。
- workflow 本地快验优先顺序为：`pwsh ./scripts/check-workflows.ps1 -Profile full` → `$env:PYTHONPATH='src'; python -m pytest tests -q` → `$env:PYTHONPATH='src'; python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json` → `$env:PYTHONPATH='src'; python -m auto_report.cli build-ops-dashboard`。
- 如需准备人工复核议题，可直接运行 `python -m auto_report.cli build-review-queue`；本地主动启用外部补证时再额外设置 `EXTERNAL_ENRICHMENT_ENABLED=true`。主 workflow 已默认开启，并限流到前 `2` 个高价值主题、单请求超时 `8s`。
- 当前 `run-status.json` 与私有 ops dashboard 已可观察 external enrichment 的 `attempted / succeeded / failed / skipped / success_rate / circuit`，接手排障时优先看这两处。
- `run-status.json` 现在还会统一写入 `publication_mode`、`review`、`ai_metrics`、`source_health` 与 `source_stats.report_topics`，用于区分轨道、审核信息、AI 调用和来源健康状况。
- 主 workflow 已会自动消费 review queue 并创建 `[V7 review]` issue；本地命令仍适合做预览和排查。
- 运行 `$env:PYTHONPATH='src'; python -m pytest tests -q` 以确认测试通过；更多测试组合也写在 USER_GUIDE。

## 本轮真实验收提醒

- 2026-04-12 的线下 reviewed 实跑已验证三端送达成功，review queue 也能产出候选 issue。
- 同日首次线上手动运行 `Collect And Report`（run id `24289432310`）在 `workflow-guard` 被 `actionlint` 拦下，原因是 `reusable-pages.yml` 的 shell 写法不安全；这说明“本地跑过一次”不能替代“线上真实 run 一次”。
- 这次还顺带暴露了两个接手高频坑：后置 issue job 需要以 artifact 是否存在为前提，Pages 构建必须跟随当前触发分支而不是固定 `main`。
- 当前本地已补上对应修复并通过 workflow guard / 测试；若要完成修复后的线上复验，需要在允许推送后再触发一次 workflow。

## 对接检查清单

- GitHub 仓库 `Actions > General > Workflow permissions` 必须为 `Read and write permissions`，否则 `report` / `deploy-pages` 无法自动回写 `data/` 与 `docs/`。
- GitHub Secrets 至少补齐 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。
- 首次接手先执行 `$env:PYTHONPATH='src'; python -m auto_report.cli diagnose-delivery --mode canary`，确认三端配置被识别；需要实发时再执行 `$env:PYTHONPATH='src'; python -m auto_report.cli diagnose-delivery --mode canary --send`、`$env:PYTHONPATH='src'; python -m auto_report.cli diagnose-delivery --mode full-report --send` 或 `AUTO_PUSH_ENABLED=true python -m auto_report.cli run-once`。
- 远端验收以 `data/state/run-status.json` 中的 `delivery_results` 为准，不要只看 workflow 是否没有抛异常。

## 审计与历史记录

- `docs/superpowers/` 保留 Stage 1~V6 的状态与审计材料，不要以文档形式重复其内容。
- `docs/upgrade-plan/` 统一保存升级计划、实现对齐审计与下一阶段续篇；回顾规划背景时优先从这里进入。
- 不要改写 audit 目录下的文件；如果需要复核历史决策，提升为新文档或注释即可。

## 需要关注的问题

- 保持 README → USER_GUIDE → TECHNICAL_GUIDE → ARCHITECTURE → push-channels-guide 的阅读顺序，防止内容散落。
- 任何新的配置（如 AI 提供商切换、推送新渠道）先在 Technical Guide 记录，再在对应运营或架构文档更新引用。
- 交接资料之外的非正式笔记请放到 `notes/` 或个人空间，避免再次写入正式文档权责区。
