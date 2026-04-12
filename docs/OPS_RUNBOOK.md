# VS_AI 运维操作手册

这份手册面向值班、验收、上线和故障排查。

目标只有一个：让维护者在最短时间内判断系统是否健康，并知道下一步该做什么。

## 1. 一页总览

- 仓库目录：`D:\GitHub\auto`
- 每日主链路：北京时间 `07:00`
- 主 workflow：`.github/workflows/collect-report.yml`
- 状态权威文件：`data/state/run-status.json`
- 公开站目录：`docs/`
- 报告目录：`data/reports/`
- 当前测试基线：`191 passed`

## 2. 每日值班检查

每天建议按这个顺序检查：

1. 看 GitHub Actions 中最新的 `Collect And Report` 是否成功
2. 看 `data/state/run-status.json` 中的：
   - `publication_mode`
   - `delivery_results`
   - `risk_level`
   - `source_health`
   - `ai_metrics`
3. 看公开站首页是否可访问：
   - `https://wsysgz.github.io/VS_AI/`
4. 抽查至少一个推送渠道的实际消息

如果第 2 步正常，说明这次运行结果基本可信。

## 3. 上传前本地验收

上传前统一执行：

```powershell
cd D:\GitHub\auto
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
- `pytest` 通过
- 本地 `reviewed` 跑通
- Pages 可重建
- 工作区没有异常未跟踪文件

## 4. 远端验收

常规远端验收顺序：

1. 推送代码
2. 手动触发 `Collect And Report`
3. 等待 run 完成
4. 核对远端产物
5. 抽查实际消息

典型命令：

```powershell
git push origin HEAD:main
gh workflow run "Collect And Report" -R wsysgz/VS_AI -f push_enabled=true -f publication_mode=reviewed
gh run watch --exit-status
```

远端必须核对：

- `data/state/run-status.json`
- `docs/index.html`
- `docs/weekly/`
- `docs/special/`
- `docs/feed.json`
- `docs/rss.xml`

注意：

- `workflow_dispatch` 运行的是远端代码，不是你本地未推送的修改
- workflow 页面为绿色，不代表消息一定送达
- 真正的送达结果仍以 `run-status.json > delivery_results` 为准

## 5. workflow 对照表

| Workflow | 作用 | 出问题时看什么 |
|---|---|---|
| `collect-report.yml` | 每日主链路 | 全链路是否正常 |
| `backfill-report.yml` | 指定日期补报 | 历史补跑、归档刷新 |
| `compensate-report.yml` | 主链路失败后的补偿 | 是否完成缺口补发 |
| `delivery-canary.yml` | 通道健康探测 | 通道配置、网络、凭据 |
| `reusable-workflow-guard.yml` | workflow 本地与 CI 校验 | YAML、shell、动作契约 |
| `reusable-python-test.yml` | Python 测试矩阵 | 代码逻辑回归 |
| `reusable-report.yml` | 渲染与推送 | 报告生成、消息送达、数据回写 |
| `reusable-pages.yml` | Pages 站点构建 | 首页、周报、专题、feeds |
| `reusable-ops-dashboard.yml` | 私有看板构建 | ops artifact |
| `reusable-review-queue.yml` | 复核队列构建 | review issue payload |

## 6. 核心产物说明

### 运行状态

- `data/state/run-status.json`

关键字段：

- `publication_mode`
- `review`
- `delivery_results`
- `risk_level`
- `source_health`
- `ai_metrics`
- `source_stats.report_topics`
- `external_enrichment`

### 报告结果

- `data/reports/latest-summary.*`
- `data/reports/latest-summary-auto.*`
- `data/reports/latest-summary-reviewed.*`

### 页面结果

- `docs/index.html`
- `docs/archives/`
- `docs/weekly/`
- `docs/special/`
- `docs/feed.json`
- `docs/rss.xml`

## 7. 故障排查顺序

### 场景 A：workflow 直接失败

先判断失败在哪一层：

1. `workflow-guard`
2. `test`
3. `collect`
4. `analyze`
5. `report`
6. `deploy-pages`

对应本地动作：

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
```

### 场景 B：workflow 成功，但消息没送达

直接看：

- `data/state/run-status.json > delivery_results`

排查命令：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli diagnose-delivery --mode canary
python -m auto_report.cli diagnose-delivery --mode canary --send
python -m auto_report.cli diagnose-delivery --mode full-report --send
```

### 场景 C：报告更新了，但页面没更新

先本地重建：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

再看：

- `docs/index.html`
- `docs/weekly/index.html`
- `docs/special/index.html`
- `docs/feed.json`
- `docs/rss.xml`

### 场景 D：需要补发或补档

本地：

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli backfill --target-date YYYY-MM-DD
```

或远端：

- 触发 `Backfill Report`

### 场景 E：高风险或复核议题出现

重点看：

- `risk_level`
- `external_enrichment`
- `out/review-queue/review-issues.json`

主 workflow 会自动消费 review queue 并创建复核 issue。

## 8. 三个重要的操作习惯

### 1. 先看状态文件，再看页面

`run-status.json` 比页面更接近真实运行结果。

### 2. 先本地过，再推远端

本地流程通过后再 push，可以显著降低线上试错成本。

### 3. 线上复跑前必须先推送

这是 GitHub Actions 最容易踩的坑之一。

## 9. 推荐阅读顺序

1. `README.md`
2. 本文
3. `USER_GUIDE.md`
4. `HANDOFF.md`
