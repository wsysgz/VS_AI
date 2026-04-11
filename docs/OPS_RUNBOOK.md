# VS_AI 运维接手 Runbook

> 最后更新：2026-04-12
> 目标：让新的维护者在 30 分钟内恢复日常运维能力，并知道从哪里看 V7 当前真实进度。

## 一页接手

- 仓库根目录：`D:\GitHub\auto`
- 每日主链路：北京时间 `07:00` 由 `Collect And Report` workflow 生成日报并推送
- 状态权威文件：`data/state/run-status.json`
- 公开产物目录：`docs/`
- 私有运维产物目录：`out/`
- 当前 V7 进度权威文档：`docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`

建议接手顺序：

1. 先读 `README.md`
2. 再读 `docs/HANDOFF.md`
3. 然后直接用本文件执行接手与排障
4. 需要详细命令时再读 `docs/USER_GUIDE.md`
5. 需要变量和渠道细节时再读 `docs/TECHNICAL_GUIDE.md` 与 `docs/push-channels-guide.md`

## 首次接手 30 分钟清单

1. 确认本地环境可用：`python -m venv .venv`、激活虚拟环境、`pip install -r requirements.txt`、`pip install -e .`
2. 检查 `.env` 或 GitHub Secrets 是否包含 `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY` / `AI_API_KEY`、`PUSHPLUS_TOKEN`、`TELEGRAM_*`、`FEISHU_*`
3. 跑 `python -m auto_report.cli diagnose-delivery --mode canary`
4. 跑 `python -m pytest tests -q`
5. 跑 `python -m auto_report.cli run-once`
6. 检查 `data/state/run-status.json`、`data/reports/latest-summary.md`
7. 跑 `python -m auto_report.cli build-pages`
8. 检查 `docs/index.html`、`docs/weekly/index.html`、`docs/special/index.html`

如果上面 8 步都通过，说明本地接手已经恢复到可运营状态。

进入本地验证前，建议先在当前 PowerShell 会话执行一次：`$env:PYTHONPATH='src'`。这台机器存在多 worktree / 多安装源时，裸跑 `python -m pytest` 或 `python -m auto_report.cli` 可能会导入到错误的 `auto_report` 路径。

## 命令入口

| 命令 | 用途 | 关键输出 |
|------|------|----------|
| `python -m auto_report.cli run-once [--publication-mode reviewed]` | 本地跑完整采集、分析、渲染、推送 | `data/reports/latest-summary.*`、`latest-summary-auto.*` / `latest-summary-reviewed.*`、`data/state/run-status.json` |
| `python -m auto_report.cli backfill --target-date YYYY-MM-DD [--publication-mode reviewed]` | 补跑指定日期，并刷新归档与站点 | `data/archives/`、`docs/archives/` |
| `python -m auto_report.cli diagnose-delivery --mode canary` | 只检查三端配置，不实发 | `run-status.json` 中的 delivery 诊断 |
| `python -m auto_report.cli diagnose-delivery --mode canary --send` | 发送 canary 消息 | 各通道实发结果 |
| `python -m auto_report.cli diagnose-delivery --mode full-report --send` | 用各渠道生产模板做实发诊断 | 各通道正文送达结果 |
| `python -m auto_report.cli collect-only` | 只做采集和预处理 | 中间态数据 |
| `python -m auto_report.cli analyze-only` | 基于已有数据执行分析 | 新的报告 payload |
| `python -m auto_report.cli render-report` | 重新渲染报告但不重采集 | 最新报告文件 |
| `python -m auto_report.cli build-pages` | 重建公开 Pages 站点、周报页与专题页 | `docs/index.html`、`docs/archives/`、`docs/weekly/`、`docs/special/`、feeds |
| `python -m auto_report.cli build-ops-dashboard` | 重建私有运营看板 | `out/ops-dashboard/index.html` |
| `python -m auto_report.cli build-review-queue` | 为高价值主题生成人工复核 issue payload | `out/review-queue/review-issues.json` |
| `python -m auto_report.cli evaluate-prompts --dataset <path>` | 做离线 Prompt/Eval 回归 | `out/evals/prompt-eval-*.json` |
| `pwsh ./scripts/check-workflows.ps1` | 跑 workflow guard、本地 workflow 快验 | 本地 workflow 校验结果 |

## 产物地图

### 公开产物

- `docs/index.html`：公开首页
- `docs/archives/`：日报归档页
- `docs/weekly/`：周报索引与周详情页
- `docs/special/`：专题聚合页，当前包含 `verified` 与 `risk-watch`
- `docs/search-index.json`：站内搜索数据
- `docs/feed.json`：JSON Feed
- `docs/rss.xml`：RSS

### 运行态与日报文件

- `data/reports/latest-summary.md`：最新日报 Markdown
- `data/reports/latest-summary.html`：最新日报 HTML
- `data/reports/latest-summary.json`：最新日报结构化 payload
- `data/reports/latest-summary-auto.*` / `latest-summary-reviewed.*`：双轨发布的轨道化最新文件
- `data/archives/YYYY-MM-DD/`：历史归档原始文件
- `data/state/run-status.json`：阶段状态、风险、调度来源、送达状态、`publication_mode`，以及 external enrichment 运行指标的权威记录

### 私有运维产物

- `out/ops-dashboard/index.html`：私有 dashboard，聚合运行状态与 prompt-eval 趋势
- `out/evals/prompt-eval-*.json`：离线评测历史结果
- `out/review-queue/review-issues.json`：人工复核 issue 草稿 payload

### 审计与规划材料

- `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`：V7 当前进度权威视图
- `docs/upgrade-plan/`：升级计划、对齐矩阵、后续收口材料
- `docs/superpowers/`：历史审计与 handoff 资料，只读参考，不作为运维入口

## Workflow 对应关系

| Workflow | 作用 | 何时看它 |
|----------|------|----------|
| `collect-report.yml` | 主日报 workflow，含定时与手动触发 | 每日 07:00 主链路、人工手动补跑主流程 |
| `backfill-report.yml` | 单日补报并刷新站点 | 某天缺报或历史回填 |
| `delivery-canary.yml` | 定时或手动做通道 canary 检测 | 怀疑推送通道失联、排查 secrets |
| `compensate-report.yml` | 错峰补偿运行 | 主日报因调度问题缺失时 |
| `reusable-collect.yml` | 采集子流程 | 排查数据源或预处理异常 |
| `reusable-analyze.yml` | 分析子流程 | 排查 AI 分析、intelligence、prompt 相关问题 |
| `reusable-report.yml` | 渲染与推送主子流程 | 排查报告生成、送达失败、风险写回 |
| `reusable-pages.yml` | Pages 构建子流程 | 排查首页、归档、周报、feeds |
| `reusable-ops-dashboard.yml` | dashboard 构建子流程 | 排查私有运营看板 |
| `reusable-review-queue.yml` | 复核 issue payload 与 issue 创建链路 | 排查 `[V7 review]` issue 未创建 |
| `reusable-python-test.yml` | Python 测试矩阵 | 排查 CI 测试失败 |
| `reusable-workflow-guard.yml` | workflow guard、actionlint、act | 排查 workflow 结构变更导致的问题 |

## 建议验收顺序

### 本地最小验收

1. `pwsh ./scripts/check-workflows.ps1`
2. `$env:PYTHONPATH='src'; python -m pytest tests -q`
3. `$env:PYTHONPATH='src'; python -m auto_report.cli diagnose-delivery --mode canary`
4. `$env:PYTHONPATH='src'; python -m auto_report.cli run-once`
5. `$env:PYTHONPATH='src'; python -m auto_report.cli build-pages`
6. `$env:PYTHONPATH='src'; python -m auto_report.cli build-ops-dashboard`
7. `$env:PYTHONPATH='src'; python -m auto_report.cli build-review-queue`
8. 需要做 PromptOps 回归时再跑 `$env:PYTHONPATH='src'; python -m auto_report.cli evaluate-prompts --dataset <path>`

### 远端验收

1. 看 workflow 是否成功
2. 读 `data/state/run-status.json`，确认 `stage_status`、`delivery_results`、`risk_level`、`scheduler`、`external_enrichment`
3. 如果本轮不是默认自动轨，再确认 `publication_mode` 与 `generated_files` 中的 `latest-summary-auto.*` / `latest-summary-reviewed.*` 是否一致
4. 确认 `docs/index.html`、`docs/weekly/`、`docs/special/`、`docs/feed.json`、`docs/rss.xml` 已更新；同日双轨同时存在时，公开页应优先显示 reviewed
5. 如果存在 review queue，确认 `[V7 review]` issue 是否按预期创建
6. 如果是风险告警，确认 reliability issue 是否包含通道、阶段、调度与风险摘要

## 失败排查顺序

### 1. workflow 红了

- 先看是 `workflow guard` / `python test` / `report` / `pages` 哪个 job 失败
- 如果是 workflow 结构问题，先跑 `pwsh ./scripts/check-workflows.ps1`
- 如果是 Python 逻辑问题，优先用 `$env:PYTHONPATH='src'; python -m pytest tests -q`

### 2. workflow 绿了，但消息没送达

- 不要只看 workflow 绿色状态
- 直接打开 `data/state/run-status.json`
- 重点看 `delivery_results.successful_channels`、`failed_channels`、各 channel 的错误摘要
- 本地复现优先用：
  - `python -m auto_report.cli diagnose-delivery --mode canary`
  - `python -m auto_report.cli diagnose-delivery --mode canary --send`
  - `python -m auto_report.cli diagnose-delivery --mode full-report --send`
  - reviewed 轨排查时，加跑 `python -m auto_report.cli run-once --publication-mode reviewed`

### 3. 报告生成了，但 Pages 没更新

- 先跑 `python -m auto_report.cli build-pages`
- 检查 `docs/index.html`、`docs/archives/`、`docs/weekly/`、`docs/special/`
- 若是补报场景，优先改走 `backfill-report.yml` 或 `backfill --target-date`

### 4. 出现高风险报告或人工复核需求

- 先看 `data/state/run-status.json` 里的 `risk_level`
- 再看 `data/state/run-status.json` 里的 `external_enrichment`，确认 `success_rate`、`failed`、`skipped`、`circuit_open`
- 再看 `out/review-queue/review-issues.json`
- 主 workflow 已会自动消费 review queue 并创建 `[V7 review]` issue
- 本地默认关闭外部补证；如需手工复现，设置 `EXTERNAL_ENRICHMENT_ENABLED=true`
- 正式 workflow 中外部补证默认开启，但已限流为前 `2` 个高价值主题、单请求超时 `8s`

### 5. Prompt 变更后质量下降

- 跑 `python -m auto_report.cli evaluate-prompts --dataset <path>`
- 对比 `out/evals/` 中最近几次结果
- 再打开 `out/ops-dashboard/index.html` 看最近 prompt-eval 趋势

## V7 当前进度与未完项

### 已稳定落地

- Phase 6：workflow engineering 主体完成，已具备 reusable workflows、workflow guard、Python matrix、`max-parallel`
- Phase 7：delivery reliability 主体完成，已覆盖 canary、full-report、三类 reliability issue
- Phase 8：prompt registry、legacy prompt 兼容、离线 prompt eval、dashboard 趋势视图已完成
- Phase 9：跨日主线记忆、生命周期、`risk_level`、support evidence、review queue 已完成主链路
- Phase 10：公开站首页、归档、搜索、feeds、周报页已落地

### 仍需继续收口

- Phase 8：长期 benchmark dataset 治理，token / latency 统一纳入 dashboard
- Phase 9：外部 enrichment 命中率、source budget 和生命周期规则继续硬化
- Phase 10：周报与首版专题聚合页已落地；渠道模板层已形成 PushPlus `short` / Feishu `medium` / Telegram `long` 的基础分层，`auto / reviewed` 双轨也已形成最小闭环；后续主要是继续丰富模板族与 reviewed 元数据

接手时不要按“从零重做”理解 V7；当前更适合按“现有基线稳定化 + 缺口逐个收口”推进。

## 接手人注意事项

- 不要改写 `docs/superpowers/` 中的历史审计文件
- 任何新的正式操作说明，优先写回 `README.md`、`docs/HANDOFF.md`、`docs/USER_GUIDE.md`、本文件
- 不要把私有运维产物发布到公开 Pages
- 远端判断送达成功时，以 `run-status.json` 为准，而不是只看 workflow 页面
- 如果只想确认当前完成度，先看 `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`

## 关联文档

- [HANDOFF.md](HANDOFF.md)
- [USER_GUIDE.md](USER_GUIDE.md)
- [TECHNICAL_GUIDE.md](TECHNICAL_GUIDE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [push-channels-guide.md](push-channels-guide.md)
- [upgrade-plan/V7_状态矩阵_2026-04-11.md](upgrade-plan/V7_状态矩阵_2026-04-11.md)
