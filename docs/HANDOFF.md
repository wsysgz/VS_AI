# VS_AI 接手手册

> **最后更新**: 2026-04-11  
> **目标**: 为每天北京时间 07:00 的综合报道提供一个清晰的路径图，确保接手者可以迅速恢复系统运行。

## 接手入口

1. `README.md`
2. `docs/USER_GUIDE.md`
3. `docs/TECHNICAL_GUIDE.md`
4. `docs/ARCHITECTURE.md`
5. `docs/push-channels-guide.md`

## 审计资料

- `docs/superpowers/`
- `docs/upgrade-plan-v6/`

## 维护流程（执行顺序）

- 阅读 `AGENTS.md` 以掌握快速查阅要点（认证、验证顺序、主要脚本）。
- 按照 README 和 USER_GUIDE 的指引设置 `.venv`、依赖、`.env`（关键变量包含 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`FEISHU_*`，更多详情在 Technical Guide）。
- 先运行 `python -m auto_report.cli diagnose-delivery` 检查三端配置，再执行 `python -m auto_report.cli run-once`，检查 `data/reports/latest-summary.md`、`data/state/run-status.json` 是否包含期望输出。
- 确保每日 07:00 的自动推送按计划执行：`Collect And Report` workflow 的 `schedule` 触发会调用 PushPlus（短摘要）和其他通道（完整报告），详见 push-channels guide。
- 运行 `python -m pytest tests -q` 以确认测试通过；更多测试组合也写在 USER_GUIDE。

## 对接检查清单

- GitHub 仓库 `Actions > General > Workflow permissions` 必须为 `Read and write permissions`，否则 `report` / `deploy-pages` 无法自动回写 `data/` 与 `docs/`。
- GitHub Secrets 至少补齐 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。
- 首次接手先执行 `python -m auto_report.cli diagnose-delivery`，确认三端配置被识别；需要实发时再执行 `python -m auto_report.cli diagnose-delivery --send` 或 `AUTO_PUSH_ENABLED=true python -m auto_report.cli run-once`。
- 远端验收以 `data/state/run-status.json` 中的 `delivery_results` 为准，不要只看 workflow 是否没有抛异常。

## 审计与历史记录

- `docs/superpowers/` 保留 Stage 1~V6 的状态与审计材料，不要以文档形式重复其内容。
- `docs/upgrade-plan-v6/` 仍保存升级计划与阶段总结，当需要回顾规划背景时再查阅。
- 不要改写 audit 目录下的文件；如果需要复核历史决策，提升为新文档或注释即可。

## 需要关注的问题

- 保持 README → USER_GUIDE → TECHNICAL_GUIDE → ARCHITECTURE → push-channels-guide 的阅读顺序，防止内容散落。
- 任何新的配置（如 AI 提供商切换、推送新渠道）先在 Technical Guide 记录，再在对应运营或架构文档更新引用。
- 交接资料之外的非正式笔记请放到 `notes/` 或个人空间，避免再次写入正式文档权责区。
