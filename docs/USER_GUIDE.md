# VS_AI 用户手册

这份手册面向“使用系统的人”，重点回答三个问题：

- 怎么把系统跑起来
- 怎么生成和查看日报
- 怎么完成日常使用中最常见的几个动作

如果你负责值班、验收、排障，请优先看 [OPS_RUNBOOK.md](OPS_RUNBOOK.md)。
如果你要接手开发和维护，请看 [HANDOFF.md](HANDOFF.md)。

## 1. 5 分钟启动

在仓库根目录执行：

```powershell
cd D:\GitHub\auto
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env
```

在 `.env` 中填写至少以下配置：

- AI：
  - `DEEPSEEK_API_KEY`
  - 或 `OPENAI_API_KEY` / `AI_API_KEY`
- 推送：
  - `PUSHPLUS_TOKEN`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `FEISHU_APP_ID`
  - `FEISHU_APP_SECRET`
  - `FEISHU_CHAT_ID`

然后在当前 PowerShell 会话中执行：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once
```

## 2. 你会得到什么

一次完整运行后，最常看的结果是：

- `data/reports/latest-summary.md`
  - 最新 Markdown 报告
- `data/reports/latest-summary.html`
  - 最新 HTML 报告
- `data/reports/latest-summary.json`
  - 结构化结果
- `data/state/run-status.json`
  - 本次运行状态、推送结果、风险等级、AI 指标

如果你运行的是人工复核版，还会看到：

- `data/reports/latest-summary-reviewed.md`
- `data/reports/latest-summary-reviewed.html`
- `data/reports/latest-summary-reviewed.json`

## 3. 最常用的 6 个场景

### 场景 A：生成当天日报

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once
```

适合：

- 本地功能确认
- 看今天会生成什么内容
- 检查推送是否正常

### 场景 B：生成人工复核版

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>
```

适合：

- 需要保留 reviewed 轨输出
- 需要在通知和页面中显示复核信息

如果暂时不想填写复核信息，也可以只指定：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once --publication-mode reviewed
```

### 场景 C：只重建公开站

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

适合：

- `data/` 已经是新的，只想刷新 `docs/`
- 想检查首页、归档页、周报页、专题页

### 场景 D：补跑某一天

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli backfill --target-date YYYY-MM-DD
```

如果需要补一条 reviewed 版本：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli backfill --target-date YYYY-MM-DD --publication-mode reviewed --reviewer <name> --review-note <text>
```

### 场景 E：检查推送配置，不实际发送

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli diagnose-delivery --mode canary
```

适合：

- 首次配置完成后的连通性检查
- 怀疑某个通道配置不完整

### 场景 F：做一次完整发布前验收

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
```

当前测试基线：`191 passed`

## 4. 报告和页面怎么看

### 本地报告

优先看：

- `data/reports/latest-summary.md`
- `data/reports/latest-summary-reviewed.md`
- `data/state/run-status.json`

### 公开站

首页入口固定为：

- `https://wsysgz.github.io/VS_AI/`

本地重建后可直接看：

- `docs/index.html`
- `docs/archives/index.html`
- `docs/weekly/index.html`
- `docs/special/index.html`

### 推送消息

三条推送正文都会同时带两个阅读入口：

- `公开阅读： https://wsysgz.github.io/VS_AI/`
- `GitHub 原文： 当前 latest-summary 对应链接`

## 5. run-status.json 怎么看

`data/state/run-status.json` 是最重要的状态文件。

重点字段：

- `publication_mode`
  - 当前是 `auto` 还是 `reviewed`
- `delivery_results`
  - 哪些通道成功、失败、跳过
- `review`
  - `reviewer` 和 `review_note`
- `ai_metrics`
  - provider、model、calls、token_usage、latency_seconds
- `source_health`
  - 来源异常统计
- `source_stats.report_topics`
  - 本轮入报主题数
- `risk_level`
  - 风险等级

如果你只想判断“这次到底发没发出去”，先看：

- `delivery_results.successful_channels`
- `delivery_results.failed_channels`

## 6. 常见问题

### 1. 运行成功了，但公开站没更新

`run-once` 不会自动刷新 `docs/`。

需要补执行：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

### 2. workflow 是绿的，但我不确定消息有没有真正送达

不要只看 GitHub Actions 颜色。

直接看：

- `data/state/run-status.json`

以 `delivery_results` 为准。

### 3. 我本地改好了，为什么线上 rerun 没带上修复

因为 `workflow_dispatch` 只运行已经推到远端的版本。

先 push，再在线上手动触发。

### 4. 没填 AI Key 能不能跑

可以。

系统会降级到规则摘要模式，仍然生成报告和状态文件，但 AI 分析深度会下降。

### 5. 我只想先看推送配置有没有通

优先跑：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli diagnose-delivery --mode canary
```

## 7. 建议阅读顺序

### 如果你只是要用起来

1. `README.md`
2. 本文

### 如果你要值班和排障

1. `README.md`
2. `OPS_RUNBOOK.md`
3. 本文

### 如果你要接手维护

1. `README.md`
2. `HANDOFF.md`
3. `OPS_RUNBOOK.md`
4. 本文
