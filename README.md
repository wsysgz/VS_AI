# VS_AI

AI 情报采集与分析系统，聚焦 AI / 大模型 / Agent 与 AI × 电子信息的每日信号研判。

## 产品承诺

- 每天北京时间 07:00 生成一条结构化综合总报（包含分析、总结、预测）。
- PushPlus/WeChat 接收短文本摘要 + GitHub 链接；Telegram 和 Feishu 接收完整报告正文（Telegram 自动按 4096 字符分段）。
- GitHub Actions 上的 `Collect And Report` workflow 保持定时、验证、推送、归档流程；本地先开发与验证，再推送。

## 快速启动（3 步）

1. 进入仓库根目录（例如 `D:\GitHub\worktrees\auto\plan-stable-repo-takeover`）并准备 Python 环境。
2. `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → `pip install -e .`。
3. 复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY`（AI 分析必需）、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`FEISHU_APP_ID/SECRET/CHAT_ID`（可选）、`AI_MAX_ANALYSIS_TOPICS` 等配置，然后运行 `python -m auto_report.cli run-once`。更多配置细节请参阅 [docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md)。

## 正式文档权责

- **[docs/HANDOFF.md](docs/HANDOFF.md)** — 交接入口，说明先读哪个文档、后续哪里找详细操作。
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** — 常规操作与验证：如何跑本地流程、检查输出、理解生成的目录与报告。
- **[docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md)** — 环境变量与 AI 配置（DeepSeek/OpenAI）、`AI_MAX_ANALYSIS_TOPICS` 限流、无密钥时的规则摘要降级。
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 系统结构：StageTimer 阶段、目录分层、主要模块职责、数据流。
- **[docs/push-channels-guide.md](docs/push-channels-guide.md)** — PushPlus/Telegram/Feishu 的配置与验证，说明如何保持每天 07:00 的推送策略。

## 审计与历史记录

- `docs/superpowers/` 留下的交接、状态和审计材料保持只读；不要把可操作内容写入这些子目录。
- `docs/upgrade-plan-v6/` 保存阶段升级计划与历史记录。
- 任何接手前先读 `AGENTS.md` 以快速恢复上下文。
