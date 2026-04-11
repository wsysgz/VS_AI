# VS_AI 用户指南

本指南帮助维护者以日常运营为中心：本地跑 pipeline、确认每日 07:00 报告、验证推送通道，并快速定位常见的操作面板。

## 每日节奏

- `Collect And Report` workflow 每天北京时间 07:00 触发综合总报，PushPlus 发送微信短摘要，Telegram 与 Feishu 发送完整报告（分别通过 `push-channels-guide` 详细说明）。
- 本地开发时先在仓库根目录准备环境、跑一遍 `run-once`，再确认 `data/reports/latest-summary.md` 与 `data/state/run-status.json` 结果，再推送 `main`。
- 无论是工作日还是排查问题，始终以 `README → USER_GUIDE → TECHNICAL_GUIDE → ARCHITECTURE → push-channels-guide` 的顺序获取上下文，避免读到过时内容。

## 环境准备

1. `python -m venv .venv`；执行 `.venv\Scripts\Activate.ps1` 后，`pip install -r requirements.txt` + `pip install -e .`。
2. 复制 `.env.example` 为 `.env`（如果已有则跳过），填写 `DEEPSEEK_API_KEY`、`AI_PROVIDER`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID`、`FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID`，更多变量详见 [Technical Guide](TECHNICAL_GUIDE.md)。
3. `python -m auto_report.cli run-once` 触发一次完整流程。首次运行前建议先跑 `python -m pytest tests -q` 确保基础功能正常。

## 常用命令

| 命令 | 用途 | 何时使用 |
|------|------|----------|
| `python -m auto_report.cli run-once` | 全流程采集→分析→渲染→推送 | 本地验证、部署前检查 |
| `python -m auto_report.cli diagnose-delivery` | 检查三端配置，不实际发送 | 首次对接、排查 secrets / `.env` |
| `python -m auto_report.cli diagnose-delivery --send` | 向三端发送一条诊断消息 | 上线前验收、怀疑某个通道失联时 |
| `python -m auto_report.cli collect-only` | 只采集 + 预处理 | 调试数据源或减少 AI 调用 |
| `python -m auto_report.cli analyze-only` | 用已有中间数据跑 AI | 跟踪分析错误、重跑 AI |
| `python -m auto_report.cli render-report` | 只渲染报告文件 | 检查模板、推送前复核 |
| `python -m auto_report.cli backfill --target-date YYYY-MM-DD` | 补报单日历史日期 | 手动修补某天缺报 |

## 验证输出

- 查看 `data/reports/latest-summary.md` 与 `data/reports/latest-summary.html` 确认内容；`data/state/run-status.json` 记录 `generated_files`、`timings`、`stage_status` 与 `delivery_results`。
- 如果本地跑出错误，先检查 `logs/`（可通过 `auto_report.cli` 添加日志）以及 `data/state/run-status.json` 的最后一次 `stage` 记录，再根据 `push-channels-guide` 验证各通知通道。
- 运行完毕后再 `git status` 查看 `data/` 变化是否按 CI 预期被忽略，确保本地临时输出未误提交。

## 仓库对接

1. 在 GitHub 仓库中确认 `Actions > General > Workflow permissions` 为 `Read and write permissions`，否则自动回写报表和 Pages 会失败。
2. 在 GitHub Secrets 中补齐 `DEEPSEEK_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。
3. 手动触发 `Collect And Report` 时，如果需要真实推送，把 workflow input `push_enabled` 设为 `true`。
4. 远端验证优先看 `data/state/run-status.json` 中的 `delivery_results.successful_channels`，不要只看 workflow 页面是否是绿色。

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
