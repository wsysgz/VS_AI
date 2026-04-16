# AI对接手册

> 适用仓库：`D:\GitHub\auto`
> 
> 最后整理：2026-04-16

这份手册把原来的开发交接、运维操作、用户使用三类核心信息收口到一个地方，作为 VS_AI 的统一对接手册。

## 1. 项目是什么

VS_AI 不是单纯的抓取脚本，而是一条工程化的 AI 情报生产链：

```text
collect
-> dedup / classify / score
-> topic builder
-> AI pipeline (analysis / summary / forecast)
-> intelligence layer
-> render
-> publish (auto / reviewed)
-> archive
-> pages / ops dashboard / review queue
```

项目当前覆盖两个主领域：

- AI / LLM / Agent
- AI x Electronics

公开站入口固定为：

- `https://wsysgz.github.io/VS_AI/`

本地工作区固定为：

- `D:\GitHub\auto`

目标远端固定为：

- `git@github.com:wsysgz/VS_AI.git`

## 2. 仓库结构与入口

```text
.
├─ .github/workflows/    workflow 入口与 reusable workflow
├─ config/               providers、sources、domains、prompts、eval dataset
├─ data/                 reports、archives、runtime state
├─ docs/                 Pages 公开站输出
├─ scripts/              本地 workflow 校验辅助脚本
├─ src/auto_report/      应用主代码
└─ tests/                回归测试
```

核心代码入口：

- `src/auto_report/cli.py`
  - 全部 CLI 命令入口
- `src/auto_report/app.py`
  - 主编排入口，负责运行、渲染、推送、归档、状态写入
- `src/auto_report/settings.py`
  - 环境变量和配置封装
- `src/auto_report/workflow_guard.py`
  - 本地 workflow profile 校验

关键 pipeline：

- `src/auto_report/pipeline/analysis.py`
- `src/auto_report/pipeline/ai_pipeline.py`
- `src/auto_report/pipeline/intelligence.py`
- `src/auto_report/pipeline/topic_builder.py`
- `src/auto_report/pipeline/review_queue.py`
- `src/auto_report/pipeline/run_once.py`

关键集成：

- `src/auto_report/integrations/pushplus.py`
- `src/auto_report/integrations/telegram.py`
- `src/auto_report/integrations/feishu.py`
- `src/auto_report/integrations/llm_client.py`

## 3. 最重要的状态文件

运行态唯一权威文件是：

- `data/state/run-status.json`

它回答的核心问题包括：

- 这次报告是什么时候生成的
- 走的是 `auto` 还是 `reviewed`
- 哪些阶段成功/失败/回退
- 哪些渠道送达成功/失败/跳过
- 本轮风险等级如何
- 真正进入报告的主题数是多少
- AI 调用了哪个 provider/model，用了多少 token
- 当前是手动、定时还是补偿运行
- 各阶段耗时多少

重点字段：

- `generated_at`
- `publication_mode`
- `review`
- `stage_status`
- `delivery_results`
- `risk_level`
- `source_stats.report_topics`
- `source_health`
- `ai_metrics`
- `external_enrichment`
- `scheduler`
- `timings`

当前 schema 约定：

- 正式字段名是 `source_stats.report_topics`，不要回退到 `filtered_topics`
- `ai_metrics` 固定包含 `provider`、`model`、`calls`、`token_usage`、`latency_seconds`、`fallback_stages`
- `source_health` 固定按 `not_found / timeout / request_error / other` 聚合
- `reviewed` 轨允许 `reviewer`、`review_note` 为空

## 4. 环境配置

初始化：

```powershell
cd D:\GitHub\auto
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
$env:PYTHONPATH='src'
```

常用环境变量：

### AI

- `DEEPSEEK_API_KEY`
- `OPENAI_API_KEY`
- `AI_PROVIDER`
- `AI_BASE_URL`
- `AI_MODEL`

### 推送

- `PUSHPLUS_TOKEN`
- `PUSHPLUS_SECRETKEY`
- `PUSHPLUS_CHANNEL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_CHAT_ID`

### 运行控制

- `AUTO_TIMEZONE`
- `AUTO_PUSH_ENABLED`
- `DELIVERY_REQUEST_TIMEOUT`
- `PUBLICATION_MODE`

## 5. PushPlus / ClawBot 接入说明

当前仓库默认 PushPlus 渠道可走 `clawbot`，并且已经支持 OpenAPI 验证最终送达状态。

### 必备配置

`.env` 至少需要：

```env
PUSHPLUS_TOKEN=...
PUSHPLUS_SECRETKEY=...
PUSHPLUS_CHANNEL=clawbot
```

### PushPlus 后台需要确认的三件事

1. 开启开放接口
2. 配置 `secretKey`
3. 在开放接口安全设置里把调用机器的公网 IP 加到白名单

### ClawBot 额外限制

根据 PushPlus 官方文档，ClawBot 不是普通 webhook：

- 首次需要扫码绑定
- 绑定后需要主动发起一次对话
- 每下发 10 次消息后，需要再主动发起一次对话
- 每隔 24 小时，也需要有一次主动对话

因此：

- `/send` 接口返回 `code=200` 不等于微信侧一定已收到
- 现在仓库会进一步用 OpenAPI 检查：
  - `haveContextToken`
  - `delivery_status`

### 当前仓库里的判定逻辑

- `haveContextToken=1` 且 `delivery_status=2`
  - 视为真正送达成功
- OpenAPI 返回 `401/403`
  - 视为授权或安全 IP 配置问题
- `haveContextToken=0`
  - 视为 ClawBot 失活，需要用户主动发消息恢复上下文
- `delivery_status=3`
  - 视为 PushPlus 已明确判定投递失败

## 6. 常用命令

### 生成当天日报

```powershell
python -m auto_report.cli run-once
```

### 生成人工复核版

```powershell
python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>
```

如果只是先确认 reviewed 轨是否能生成：

```powershell
python -m auto_report.cli run-once --publication-mode reviewed
```

### 补报

```powershell
python -m auto_report.cli backfill --target-date YYYY-MM-DD
```

### 重渲染当前状态

```powershell
python -m auto_report.cli render-report --publication-mode auto
python -m auto_report.cli render-report --publication-mode reviewed --reviewer <name> --review-note <text>
```

### 诊断推送

```powershell
python -m auto_report.cli diagnose-delivery --mode canary
python -m auto_report.cli diagnose-delivery --mode canary --send
python -m auto_report.cli diagnose-delivery --mode full-report --send
```

### 构建公开站 / 运维产物

```powershell
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-review-queue
```

### Prompt 评估

```powershell
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
```

## 7. 本地验收基线

当前已验证基线：`200 passed`

推荐完整验收：

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-review-queue
git status --short
```

验收标准：

- workflow guard 通过
- pytest 通过
- prompt eval 通过
- reviewed 轨本地跑通
- Pages / ops dashboard / review queue 可重建
- `git status --short` 没有异常运行产物残留

## 8. workflow 拓扑

入口 workflow：

- `.github/workflows/collect-report.yml`
- `.github/workflows/backfill-report.yml`
- `.github/workflows/compensate-report.yml`
- `.github/workflows/delivery-canary.yml`

本地 workflow 校验入口：

- `scripts/check-workflows.ps1`
- `src/auto_report/workflow_guard.py`

支持固定 profile：

- `daily`
- `recovery`
- `full`

一个关键事实：

- `workflow_dispatch` 始终跑远端已 push 代码，不会读取本地未 push 修改

所以 workflow 相关改动的正确顺序必须是：

1. 本地验证
2. push 到远端
3. 再触发线上 workflow

## 9. 推送与交付约束

当前版本的重要收口约束：

1. 所有渠道消息必须同时带：
   - 公开站入口
   - GitHub 原文入口
2. `public limitations` 只保留编辑性限制，采集器异常进入 `source_health`
3. `source_health` 与 `ai_metrics` 是正式 observability 面
4. 报告时间、归档日期、`generated_at` 必须保持同一时区语义
5. reviewed 元数据允许为空

## 10. 来源清洗现状

截至 2026-04-16，已经完成第一轮安全清洗：

- `config/sources/github.yaml`
  - 将失效的 `NVIDIA/cuda-cmake` 替换为 `NVIDIA/TensorRT`
- `config/sources/websites.yaml`
  - 将长期失效的 `st-blog` 标记为 `enabled: false`
  - 将已返回 `410 Gone` 的 `ti-e2e-blog` 标记为 `enabled: false`

保留禁用槽位的原因：

- 方便后续恢复或替换，不丢失领域覆盖意图
- 未来更适合通过 RSSHub / Firecrawl / changedetection 侧车来补齐这类来源

## 11. 新维护者接手清单

建议第一次接手按这个顺序：

1. 读完本手册第 2、3、5、7、8、9、10 节
2. 跑一次完整本地验收
3. 检查：
   - `data/state/run-status.json`
   - `data/reports/latest-summary-reviewed.md`
   - `docs/index.html`
4. 抽查至少一个真实推送渠道
5. 最后确认 `git status --short` 没有异常运行产物

## 12. 最容易踩的坑

- 忘记设置 `$env:PYTHONPATH='src'`
- 只看 workflow 颜色，不核对 `delivery_results`
- 本地改了 workflow，却没 push 就去点 `workflow_dispatch`
- 只看 PushPlus `/send` 的 `code=200`，没看 ClawBot 的激活状态和最终送达状态
- 修改状态 schema 却没同步更新 dashboard、页面或测试
- 保留了长期 404/410 来源，导致 `source_health` 噪音越来越大

## 13. 推荐进一步阅读

- `README.md`
- `用户操作手册.md`
- `V1升级方案.md`
- `交接备忘录.md`
- `AGENTS.md`

## 14. 当前交接状态（2026-04-16）

这一轮已经完成并验证的核心事项：

- PushPlus / ClawBot 最终送达验证已打通，当前判定逻辑以 `haveContextToken` 和 `delivery_status` 为准
- 文档已收口为根目录统一入口，不再依赖旧的 `docs/HANDOFF.md`、`docs/OPS_RUNBOOK.md`、`docs/USER_GUIDE.md`
- 来源清洗第一轮已落地：
  - `NVIDIA/cuda-cmake` -> `NVIDIA/TensorRT`
  - `st-blog` 禁用
  - `ti-e2e-blog` 禁用
- P1 来源治理基础层已落地：
  - `source_health` 现在支持 per-source breakdown
  - ops dashboard 新增 `Source Failure Breakdown`
  - `arxiv-cs-ai` 已切到官方 Atom 查询接口

当前用户明确要求与工作偏好：

- 直接在 `main` 上工作，不创建功能分支
- Telegram 当前视为网络环境问题，不作为当前优化优先级
- 当前优先级是继续推进 P1（来源稳定性升级）
- `README.md` 和总手册的大幅改版等到 V1 基本完成后再继续做审美/结构优化

建议下一位接手者优先按这个顺序推进：

1. 为高价值脆弱来源寻找 RSSHub route
2. 形成 changedetection.io watch 清单
3. 为来源 registry 增加替代入口与稳定性分层
4. 继续增强 `source_health` 的可操作性输出

