# VS_AI

AI 情报采集与分析系统，聚焦 AI / 大模型 / Agent 与 AI × 电子信息的每日信号研判。

## 产品承诺

- 每天北京时间 07:00 生成一条结构化综合总报（包含分析、总结、预测）。
- PushPlus/WeChat 接收短文本摘要 + GitHub 链接；Feishu 接收中长度结构化摘要；Telegram 接收完整长文报告（自动按 4096 字符分段）。
- GitHub Actions 上的 `Collect And Report` workflow 保持定时、验证、推送、归档流程；本地先开发与验证，再推送。
- workflow 可靠性基线已包含 `actionlint + act + workflow guard`、Python 测试矩阵与 `max-parallel` 控制，并对“全通道失败 / 连续 canary 失败 / 高风险报告”创建 GitHub Issue。
- GitHub Pages 站点通过 `main` 分支下的 `docs/` 持续更新，`build-pages` 与 backfill workflow 会一并回写 `docs/index.html`、`docs/archives/`、`docs/weekly/`、`docs/special/`、`docs/search-index.json`、`docs/feed.json`、`docs/rss.xml`。
- Publishing Surface 已新增 `docs/weekly/` 周报页与 `docs/special/` 专题聚合页，继续复用现有 Pages 输出，不引入单独前端服务。
- 发布面现已支持 `auto / reviewed` 双轨：定时主链路默认产出 `auto`，手工 rerun / backfill 可切到 `reviewed`，并同时保留 `latest-summary-auto.*` 与 `latest-summary-reviewed.*`；公开 Pages 在同一天两条轨同时存在时优先展示 reviewed。
- PromptOps 已提供离线评测入口：`evaluate-prompts --dataset <path>` 会把结果写入 `out/evals/`，并在私有 ops dashboard 中展示最近 prompt-eval 趋势与回归降分。
- Intelligence Layer 已提供可选开启的外部补证与 `build-review-queue` 入口，用于为高价值主题生成人工复核 issue payload。
- `run-status.json` 与私有 ops dashboard 现在还会记录 external enrichment 的 `attempted / succeeded / failed / skipped / success_rate / circuit`，方便排障与接手。
- 主 `Collect And Report` workflow 已会消费 review queue，并自动创建 `[V7 review]` 复核 issue。
- 正式 workflow 已默认启用外部补证，但会限流到前 `2` 个高价值主题、单请求超时 `8s`；本地默认仍关闭。

## Quick Start

- local workspace: `D:\GitHub\auto`
- read `docs/OPS_RUNBOOK.md` for maintainer runbook / takeover checklist
- read `docs/HANDOFF.md` for maintainer takeover
- read `docs/USER_GUIDE.md` for local run and deployment
- read `docs/push-channels-guide.md` for WeChat / Feishu / Telegram setup

## 本地启动（3 步）

1. 默认主工作区为 `D:\GitHub\auto`；如果你正在隔离 worktree 中实现变更，也沿用同一目录结构准备 Python 环境。
2. `python -m venv .venv` → `.venv\Scripts\Activate.ps1` → `pip install -r requirements.txt` → `pip install -e .`。
3. 复制 `.env.example` 为 `.env`，填写 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` / `AI_API_KEY`（按 `AI_PROVIDER` 选择；未配置时系统自动回退到规则摘要模式）、`PUSHPLUS_TOKEN`、`TELEGRAM_BOT_TOKEN`、`FEISHU_APP_ID/SECRET/CHAT_ID`（可选）、`AI_MAX_ANALYSIS_TOPICS` 等配置，然后运行 `python -m auto_report.cli run-once`。如需生成人工复核版，可改用 `python -m auto_report.cli run-once --publication-mode reviewed`，或设置 `PUBLICATION_MODE=reviewed`。更多配置细节请参阅 [docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md)。

## 正式文档权责

- **[docs/OPS_RUNBOOK.md](docs/OPS_RUNBOOK.md)** — 运维接手主 runbook，集中说明命令入口、产物位置、workflow 对应关系、失败排查顺序与 V7 当前真实进度。
- **[docs/HANDOFF.md](docs/HANDOFF.md)** — 交接入口，说明先读哪个文档、后续哪里找详细操作。
- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)** — 常规操作与验证：如何跑本地流程、检查输出、理解生成的目录与报告。
- **[docs/TECHNICAL_GUIDE.md](docs/TECHNICAL_GUIDE.md)** — 环境变量与 AI 配置（DeepSeek/OpenAI）、`AI_MAX_ANALYSIS_TOPICS` 限流、无密钥时的规则摘要降级。
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 系统结构：StageTimer 阶段、目录分层、主要模块职责、数据流。
- **[docs/push-channels-guide.md](docs/push-channels-guide.md)** — PushPlus/Telegram/Feishu 的配置与验证，说明如何保持每天 07:00 的推送策略。

## 审计与历史记录

- `docs/superpowers/` 留下的交接、状态和审计材料保持只读；不要把可操作内容写入这些子目录。
- `docs/upgrade-plan/` 统一保存升级计划、版本对齐审计与后续续篇。
- 当前 V7 真实进度请优先查看 `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`。
- 任何接手前先读 `AGENTS.md` 以快速恢复上下文。
