# AI对接手册

> 适用仓库：`D:\GitHub\auto`
>
> 目标：让新会话 AI、上下文被清空后的 AI、或第一次接手这个仓库的人，在 10 分钟内恢复到可执行状态
>
> 最后更新：2026-04-17

这份手册不是“项目介绍”，而是 VS_AI 的接管入口。它的重点是三件事：

1. 让 AI 快速建立完整工程认知
2. 让 AI 快速对接当前项目进度
3. 让 AI 在失忆后仍然知道先看什么、先做什么、先验证什么

## 0. 60 秒接管

如果你只剩 1 分钟，先记住这些绝对事实：

- 本地工作区：`D:\GitHub\auto`
- Canonical remote：`git@github.com:wsysgz/VS_AI.git`
- 默认工作分支：`main`
- 公开站入口：`https://wsysgz.github.io/VS_AI/`
- 当前本地验证基线：`210 passed`
- 当前主线优先级：`P1：来源稳定性升级`
- 运行态唯一权威文件：`data/state/run-status.json`
- 来源治理权威产物：`out/source-governance/source-governance.json`
- 手动触发 workflow 前必须先 `push`，因为 `workflow_dispatch` 只跑远端已 push 代码

如果你只剩 3 分钟，按这个顺序看：

1. `交接备忘录.md`
2. `data/state/run-status.json`
3. `out/source-governance/source-governance.json`
4. `.github/workflows/collect-report.yml`
5. 最近 5 条 `git log`

## 1. 新会话 AI 的前 10 分钟

推荐恢复顺序：

### 第 1 步：确认仓库是不是干净的

```powershell
cd D:\GitHub\auto
git status --short
git log --oneline -5
```

你要回答三个问题：

- 当前有没有未提交修改
- 最近 5 次提交在推进什么
- 这次会话是继续已有主线，还是在处理一次临时修复

### 第 2 步：读取最小上下文集

必读文件：

- `README.md`
- `AI对接手册.md`
- `交接备忘录.md`
- `V1升级方案.md`
- `data/state/run-status.json`
- `out/source-governance/source-governance.json`

这 6 个文件足够你回答：

- 项目是做什么的
- 现在做到哪了
- 现在卡在哪里
- 下一步应优先做什么
- 做完后该怎么验收和上线

### 第 3 步：建立当前状态判断

优先核对：

- `publication_mode`
- `review`
- `delivery_results`
- `risk_level`
- `source_stats.report_topics`
- `source_health`
- `source_governance`
- `ai_metrics`
- 当前激活的 `AI_PROVIDER / AI_BASE_URL / AI_MODEL`

### 第 4 步：决定这次会话属于哪一类

常见会话类型：

- 文档 / 交接 / 上下文恢复
- 来源治理 / 坏源修复
- workflow / CI 验证
- 推送 / 交付诊断
- 页面 / dashboard / review queue 输出修复

决定完类型后，再去读对应代码或配置，不要一上来全仓库漫游。

## 2. 项目是什么

VS_AI 是一条工程化的 AI 情报生产链，而不是单点脚本。主链路如下：

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

领域重点：

- AI / LLM / Agent
- AI x Electronics

输出面：

- Markdown / HTML / JSON 报告
- PushPlus / Telegram / Feishu 推送
- GitHub Pages 公开站
- ops dashboard
- source governance artifact
- review queue

## 3. 仓库地图：先看哪里最值钱

### 3.1 入口层

- `src/auto_report/cli.py`
  - 全部 CLI 命令入口
- `src/auto_report/app.py`
  - 主编排入口；负责 collect、AI、render、delivery、archive、状态写入
- `src/auto_report/settings.py`
  - 环境变量与 YAML 配置装配
- `src/auto_report/workflow_guard.py`
  - 本地 workflow profile 校验逻辑

### 3.2 pipeline 层

重点目录：`src/auto_report/pipeline/`

常看模块：

- `analysis.py`
- `ai_pipeline.py`
- `intelligence.py`
- `topic_builder.py`
- `review_queue.py`
- `run_once.py`

### 3.3 输出与交付层

- `src/auto_report/outputs/renderers.py`
- `src/auto_report/outputs/pages_builder.py`
- `src/auto_report/outputs/ops_dashboard.py`
- `src/auto_report/integrations/pushplus.py`
- `src/auto_report/integrations/telegram.py`
- `src/auto_report/integrations/feishu.py`
- `src/auto_report/integrations/llm_client.py`

### 3.4 配置层

- `config/providers.yaml`
- `config/sources/github.yaml`
- `config/sources/rss.yaml`
- `config/sources/websites.yaml`
- `config/domains/`
- `config/prompt_eval/baseline-v1.json`
- `.env`

### 3.5 运行态与产物层

- `data/state/run-status.json`
- `data/reports/latest-summary.*`
- `data/reports/latest-summary-reviewed.*`
- `out/source-governance/source-governance.json`
- `out/ops-dashboard/index.html`
- `docs/index.html`

## 4. 不要信记忆，只信这些真相源

### 4.1 运行态真相

`data/state/run-status.json` 回答这些问题：

- 本轮是 `auto` 还是 `reviewed`
- 这轮报告是否真的生成了
- 三个 AI 阶段是否成功
- 三个渠道是成功、失败还是跳过
- 风险等级如何
- 真正进入报告的主题数是多少
- 当前 provider / model / token / latency 是什么
- 这轮是手动、定时还是补偿运行

最关键字段：

- `generated_at`
- `publication_mode`
- `review`
- `stage_status`
- `delivery_results`
- `risk_level`
- `source_stats.report_topics`
- `source_health`
- `source_registry`
- `source_governance`
- `ai_metrics`
- `scheduler`
- `timings`

### 4.2 来源治理真相

`out/source-governance/source-governance.json` 回答这些问题：

- 当前来源有哪些治理候选
- 哪些来源需要 manual review
- 哪些来源适合优先找 RSSHub / feed
- 哪些来源适合建 changedetection watch
- 哪些来源已经有 `replacement_target`

当前治理摘要（2026-04-17 仓库快照）：

- `manual_review_count = 4`
- `rsshub_candidate_count = 11`
- `changedetection_candidate_count = 10`
- `replacement_candidate_count = 14`

### 4.3 远端执行真相

`.github/workflows/collect-report.yml` 回答这些问题：

- push 到 `main` 后会自动跑什么
- 手动触发时有哪些输入参数
- `push_enabled` 怎样控制真实通知发送
- 流程链路是 `workflow-guard -> test -> collect -> analyze -> report -> pages / ops / review`

最容易忘的事实：

- `workflow_dispatch` 跑的是远端 ref，不是本地未 push 的修改
- `push` 触发时忽略 `data/**`
- 手动验证远端通常优先使用 `push_enabled=false`，避免无意实际推送

## 5. 当前项目进度怎么对接

任何新会话 AI，如果要“对接项目进度”，按下面这套顺序，不要跳步：

### 5.1 看最近提交在推进什么

```powershell
git log --oneline -10
```

目标：识别最近是文档收口、来源治理、推送诊断、还是 dashboard / Pages 修复。

### 5.2 看最近一次运行出了什么结果

```powershell
Get-Content data/state/run-status.json
```

目标：确认最新结果是成功还是带风险，当前主要问题在 delivery 还是 source health。

### 5.3 看治理队列还剩什么没做

```powershell
Get-Content out/source-governance/source-governance.json
```

目标：确认 P1 还剩哪几类工作：RSSHub、changedetection、manual replace、replacement target。

### 5.4 看当前路线图

读 `V1升级方案.md`，确认：

- 当前主阶段是不是仍是 P1
- P1 的退出条件有哪些
- 下一阶段是不是 P2-A / P2-B / P2-C

### 5.5 看交接备忘录

`交接备忘录.md` 只记录“最容易丢的上下文”：

- 用户明确偏好
- 当前不做什么
- 建议下一步顺序

这份文件是最快的方向校准器。

## 6. 当前确认过的状态快照（2026-04-17）

当前确定成立的项目状态：

- 直接在 `main` 上工作，不建立功能分支
- 文档主入口已经统一收口到仓库根目录
- 当前主线优先级仍是 `P1：来源稳定性升级`
- PushPlus / ClawBot 已经不是“接口成功即成功”，而是看最终送达状态
- 本地验证基线已经提升并固定到 `210 passed`
- 本轮交接中已再次本地跑通 reviewed 验证；精确时间、主题数和风险等级以当前 `data/state/run-status.json` 为准

目前已经落地的关键收口：

- PushPlus / ClawBot 最终送达验证
- `source_health` per-source breakdown
- `source_health` failure-only 统计
- 统一 `source_registry` builder
- `source_governance` 队列与 JSON artifact
- ops dashboard 的 `Source Failure Breakdown`
- ops dashboard 的 `Source Registry` / 治理队列表格
- `arxiv-cs-ai` 切到官方 Atom 查询接口
- `NVIDIA/cuda-cmake` 替换为 `NVIDIA/TensorRT`
- `st-blog` / `ti-e2e-blog` 已禁用

最近仓库快照显示的未完成重点：

- 第一批 RSSHub route 还没真正落表
- changedetection watch 清单还没真正建立
- `OpenCLI` 侧车 pilot 还没做
- GitHub Actions 还没切到统一 provider 配置（当前仍固定 DeepSeek）
- 高价值脆弱 listing 来源仍需要补 `replacement_target` 或旁路方案

最近可见的 source failure 示例：

补充状态（2026-04-18 之后继续接手时要记住）：

- P1 的核心工程目标已经基本收口，不再建议把 P1 当成长时间阻塞项
- 下一阶段主线应转向 P2 准备与落地：
  1. 双 AI 并存与 stage routing
  2. LiteLLM Gateway
  3. Langfuse tracing
- `CLI-Anything` 已评估：暂不直接接主链
- `OpenCLI` 已评估：更适合做来源侧车 / 运维侧车，可作为 P2.5 / P3 的 pilot

- `qwen-blog`
- `openvino-blog`
- `google-ai-edge`
- `huggingface-blog`
- `meta-ai-blog`
- `arxiv-cs-ai`

这些示例说明：P1 不再是“知道要治理”，而是已经有清单、有标签、有 next action，下一步该把治理动作真正落地。

## 7. CLI 命令地图

### 7.0 AI provider 切换速查

当前仓库的 `src/auto_report/integrations/llm_client.py` 已支持 OpenAI-compatible provider。

已确认可切换的两套配置：

```powershell
# DeepSeek 官方
$env:AI_PROVIDER='deepseek'
$env:AI_BASE_URL='https://api.deepseek.com'
$env:AI_MODEL='deepseek-chat'
$env:DEEPSEEK_API_KEY='<your-deepseek-key>'

# MiniMax-M2.7（通过 OpenAI-compatible 第三方入口）
$env:AI_PROVIDER='minimax_svips'
$env:AI_BASE_URL='https://api.svips.org/v1'
$env:AI_MODEL='MiniMax-M2.7'
$env:AI_API_KEY='<your-minimax-key>'
```

注意：

- 当前已经支持按 `analysis / summary / forecast` 分阶段切换 provider。
- `DeepSeek / MiniMax` 可以在同一轮运行中并存。
- 预筛选阶段当前默认复用 `analysis` 的 provider 设置。

推荐默认分工：

```powershell
$env:ANALYSIS_AI_PROVIDER='deepseek'
$env:ANALYSIS_AI_BASE_URL='https://api.deepseek.com'
$env:ANALYSIS_AI_MODEL='deepseek-chat'

$env:SUMMARY_AI_PROVIDER='minimax_svips'
$env:SUMMARY_AI_BASE_URL='https://api.svips.org/v1'
$env:SUMMARY_AI_MODEL='MiniMax-M2.7'
$env:SUMMARY_AI_API_KEY='<your-minimax-key>'

$env:FORECAST_AI_PROVIDER='deepseek'
$env:FORECAST_AI_BASE_URL='https://api.deepseek.com'
$env:FORECAST_AI_MODEL='deepseek-chat'
```

### 7.1 每日 / 手工运行

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli run-once
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli run-once --publication-mode reviewed --reviewer <name> --review-note <text>
```

### 7.2 补报与重渲染

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli backfill --target-date YYYY-MM-DD
python -m auto_report.cli render-report --publication-mode auto
python -m auto_report.cli render-report --publication-mode reviewed --reviewer <name> --review-note <text>
```

### 7.3 构建页面与内部产物

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
```

### 7.4 诊断交付

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli diagnose-delivery --mode canary
python -m auto_report.cli diagnose-delivery --mode canary --send
python -m auto_report.cli diagnose-delivery --mode full-report --send
```

### 7.5 离线评估与 workflow 校验

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
python -m pytest tests -q
```

## 8. 本地验收、推仓、远端触发的标准顺序

只要涉及 workflow、交付、页面、状态 schema、来源治理，默认都用这个顺序：

### 8.1 本地完整验收

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
$env:AUTO_PUSH_ENABLED='false'
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
git status --short
```

通过标准：

- workflow guard 通过
- pytest 通过
- prompt eval 通过
- reviewed 轨本地跑通
- Pages / ops dashboard / source governance / review queue 能重建
- 没有异常运行产物残留
- 平时默认停在本地验证闭环；只有项目计划完成、阶段性完成、或明确需要发布级确认时，才触发远端 GitHub workflow

### 8.2 推送到远端

```powershell
git add <changed-files>
git commit -m "docs: refresh handoff manuals"
git push origin main
```

### 8.3 手动触发 GitHub workflow

先记住这条新增规则：

- 远端 workflow 不是日常调试回路，默认只在“项目计划完成 / 阶段性完成 / 发布前确认”时使用
- 只要还在中间开发阶段，就优先用本地验证解决问题，不要把 GitHub Actions 当主要排错工具
- 每次准备 `push` 或 `workflow_dispatch` 前，都先确认本地验证已经通过并且结果可信

建议优先触发 `Collect And Report`，并先把真实推送关掉：

```powershell
gh workflow run collect-report.yml --ref main -f push_enabled=false -f publication_mode=reviewed -f reviewer=manual-check -f review_note=post-push-verification
```

或者在 GitHub Actions UI 中手动点：

- Workflow：`Collect And Report`
- Branch：`main`
- `push_enabled = false`
- `publication_mode = reviewed`

### 8.4 远端核对结果

至少确认：

- `workflow-guard`、`test`、`collect`、`analyze`、`report` 都通过
- `deploy-pages`、`ops-dashboard`、`review-queue` 都通过
- 没有新出现的 reliability issue

## 9. PushPlus / ClawBot 接入要点

当前仓库默认 PushPlus 可走 `clawbot`，但判定标准已经升级：

- 不是 `/send` 返回 `code=200` 就算成功
- 必须进一步检查 OpenAPI 的最终送达状态

`.env` 至少需要：

```env
PUSHPLUS_TOKEN=...
PUSHPLUS_SECRETKEY=...
PUSHPLUS_CHANNEL=clawbot
```

PushPlus 后台要确认：

1. 开启开放接口
2. 配置 `secretKey`
3. 调用机器公网 IP 已进白名单

ClawBot 额外事实：

- 首次要扫码绑定
- 绑定后要主动发起一次对话
- 每 10 次消息需要重新主动对话一次
- 每隔 24 小时也需要一次主动对话

当前仓库中的判定逻辑：

- `haveContextToken=1` 且 `delivery_status=2` -> 真正送达成功
- `haveContextToken=0` -> ClawBot 失活，需要用户主动发消息恢复
- `delivery_status=3` -> 明确投递失败
- OpenAPI `401/403` -> 授权或安全 IP 配置问题

## 10. 最容易踩的坑

- 忘记设置 `$env:PYTHONPATH='src'`
- 只看 Actions 颜色，不看 `run-status.json`
- 改了 workflow 却没 push 就去手动 dispatch
- 把 PushPlus `/send` 的成功误认为真正送达成功
- 修改状态 schema 但没同步 dashboard / 页面 / 测试
- 把信息性诊断误记入 `source_health`
- 修完本地后忘了再核对远端 workflow 结果

## 11. 新会话 AI 启动提示词（可直接复制）

```text
你现在接手仓库 D:\GitHub\auto（VS_AI）。

先不要假设上下文仍然存在，请按下面顺序恢复：
1. 读取 README.md、AI对接手册.md、交接备忘录.md、V1升级方案.md
2. 读取 data/state/run-status.json 和 out/source-governance/source-governance.json
3. 查看 git status --short 和 git log --oneline -10
4. 说明当前项目阶段、最近已完成事项、未完成高优先级事项
5. 给出下一步建议顺序，并说明本地验证 / push / workflow_dispatch 的正确顺序

已知固定事实：
- 工作区是 D:\GitHub\auto
- 远端是 git@github.com:wsysgz/VS_AI.git
- 当前优先级是 P1：来源稳定性升级
- 运行态真相文件是 data/state/run-status.json
- 手动触发 workflow 前必须先 push
- 直接在 main 上工作，不创建功能分支
- Telegram 暂不作为当前优化优先级
```

## 12. AI 接手后的首小时清单

建议第一小时只做下面这些高价值动作：

1. 确认仓库干净、确认最近提交方向
2. 读取 `run-status.json` 和 `source-governance.json`
3. 判断当前工作属于：文档、来源治理、workflow、推送诊断、页面输出中的哪一类
4. 如果是代码或配置改动，先定义本地验收命令
5. 完成本地验证后再考虑 `push` 与远端 dispatch

如果你是临时接手，不确定该优先干什么，默认优先：

1. P2-A：双 AI 并存 + stage routing
2. P2-B：LiteLLM Gateway
3. P2-C：Langfuse tracing
4. P2.5：OpenCLI sidecar pilot
5. workflow / delivery 的可验证性
