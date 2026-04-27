# AI对接手册

> 适用仓库：`D:\GitHub\auto`
>
> 目标：让新会话 AI、上下文被清空后的 AI、或第一次接手这个仓库的人，在 10 分钟内恢复到可执行状态
>
> 最后更新：2026-04-28

这份手册不是“项目介绍”，而是 VS_AI 的接管入口。它的重点是三件事：

1. 让 AI 快速建立完整工程认知
2. 让 AI 快速对接当前项目进度
3. 让 AI 在失忆后仍然知道先看什么、先做什么、先验证什么

新增执行原则（2026-04-19 起默认执行）：

- 项目推进尽量按阶段整段推进，不在多个阶段之间来回磨
- 当前阶段没有完成本地闭环前，不要把注意力切去做下一阶段的表层优化
- 新想法如果属于后续阶段，先写入路线图，再回到当前阶段收口

## 0. 60 秒接管

如果你只剩 1 分钟，先记住这些绝对事实：

- 本地工作区：`D:\GitHub\auto`
- Canonical remote：`git@github.com:wsysgz/VS_AI.git`
- 默认工作分支：`main`
- 公开站入口：`https://wsysgz.github.io/VS_AI/`
- 当前本地验证基线：`337 passed`
- 当前主线优先级：`公开站 IA V2 第一批已完成、已推送、已远端确认；下次先回看手动补触发 run 25009334909，再评估 IA V2 第二批`
- 上一轮远端 `Collect And Report` 已全链路通过：`2026-04-22 / run 24762469538 / commit 46c47ef`
- 当前最新远端 `Collect And Report` 已成功：`2026-04-28 / push run 25009309491 / trigger commit d743668 / output commit ba23ec5 / https://github.com/wsysgz/VS_AI/actions/runs/25009309491`
- 当前待回看远端 `Collect And Report`：`2026-04-28 / workflow_dispatch run 25009334909 / commit d743668 / 截至 01:46 已通过 analyze，正在 report / https://github.com/wsysgz/VS_AI/actions/runs/25009334909`
- 当前最新远端 `Delivery Canary` 已成功：`2026-04-24 / run 24864175041 / commit 780dcfd`
- 当前最新远端 `Source Reachability Canary` 已成功：`2026-04-24 / run 24864003455 / commit 780dcfd`
- GitHub Repository Variables 已切换到 DeepSeek V4 默认路由：`analysis/summary/forecast=pro`，`prefilter/discovery/search=flash`
- 运行态唯一权威文件：`data/state/run-status.json`
- 来源治理权威产物：`out/source-governance/source-governance.json`
- 本地 watch 真相文件：`out/source-governance/changedetection-watch-registry.json` / `out/source-governance/watch-run-results.json`
- 手动触发 workflow 前必须先 `push`，因为 `workflow_dispatch` 只跑远端已 push 代码

如果你只剩 3 分钟，按这个顺序看：

1. `交接备忘录.md`
2. `data/state/run-status.json`
3. `out/source-governance/source-governance.json`
4. `.github/workflows/collect-report.yml`
5. 最近 5 条 `git log`

下次接手第一条动作：

```powershell
git pull --ff-only origin main
gh run view 25009334909 --repo wsysgz/VS_AI --json status,conclusion,url,updatedAt
```

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

补充执行纪律：

- 如果当前会话已经确认处于 `P2-B LiteLLM Gateway`，就先把 Gateway 接入、文档、测试、回退路径做完
- 当前默认阶段顺序已经切到：`P3-C` 已完成，下一步先讨论公开站整理 / 优化方案；不要把公开站讨论和来源治理尾项、OpenCLI pilot 混做

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
- Feishu 推送
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

当前治理摘要（以当前仓库 artifact 为准）：

- `manual_review_count = 1`
- `rsshub_candidate_count = 4`
- `changedetection_candidate_count = 4`
- `replacement_candidate_count = 5`
- `changedetection_watch_registry.status_counts.active_local = 4`

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
- 当前远端 workflow 已支持统一 provider 配置与 stage-level routing，并已完成远端验证

### 4.4 远端 AI provider 配置真相

远端 GitHub Actions 现在分三层看：

1. 默认层
   - `AI_PROVIDER=deepseek`
   - `AI_BASE_URL=https://api.deepseek.com`
   - `AI_MODEL=deepseek-v4-flash`
   - Secret 仍以 `DEEPSEEK_API_KEY` 为默认主路径
2. 全局切换层
   - Repository Variables:
     - `AI_PROVIDER`
     - `AI_BASE_URL`
     - `AI_MODEL`
   - Repository Secret:
     - `AI_API_KEY`
3. stage-level routing 层
   - Variables:
     - `ANALYSIS_AI_PROVIDER`
     - `ANALYSIS_AI_BASE_URL`
     - `ANALYSIS_AI_MODEL`
     - `SUMMARY_AI_PROVIDER`
     - `SUMMARY_AI_BASE_URL`
     - `SUMMARY_AI_MODEL`
     - `FORECAST_AI_PROVIDER`
     - `FORECAST_AI_BASE_URL`
     - `FORECAST_AI_MODEL`
     - `PREFILTER_AI_PROVIDER`
     - `PREFILTER_AI_BASE_URL`
     - `PREFILTER_AI_MODEL`
     - `DISCOVERY_AI_PROVIDER`
     - `DISCOVERY_AI_BASE_URL`
     - `DISCOVERY_AI_MODEL`
     - `SEARCH_AI_PROVIDER`
     - `SEARCH_AI_BASE_URL`
     - `SEARCH_AI_MODEL`
   - Secrets:
     - `ANALYSIS_AI_API_KEY`
     - `SUMMARY_AI_API_KEY`
     - `FORECAST_AI_API_KEY`
     - `PREFILTER_AI_API_KEY`
     - `DISCOVERY_AI_API_KEY`
     - `SEARCH_AI_API_KEY`

当前远端验证结论：

- `analysis` -> DeepSeek
- `summary` -> MiniMax-M2.7
- `forecast` -> DeepSeek
- `prefilter` -> MiniMax-M2.7

后续远端验证建议：

- 先 `push`
- 再手动触发 `Collect And Report`
- 先用 `push_enabled=false`
- 先确认 `run-status.json` 里的 provider / model / ai_metrics 是否符合预期
- 确认无误后再打开真实推送

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

- 当前主阶段是不是已经切到 `P3-A / P3-B`
- `P3-A` 当前还剩哪些收口项（`Delivery Canary` 已升级为飞书卡片主路径 canary，剩余以交付面小修为主）
- `P3-B` 当前是否只是铺底，还是已经进入正式实现

### 5.5 看交接备忘录

`交接备忘录.md` 只记录“最容易丢的上下文”：

- 用户明确偏好
- 当前不做什么
- 建议下一步顺序

这份文件是最快的方向校准器。

## 6. 当前确认过的状态快照（2026-04-28）

当前确定成立的项目状态：

- 直接在 `main` 上工作，不建立功能分支
- 文档主入口已经统一收口到仓库根目录
- 当前主线已完成 `P3-B 阶段性收口 + P3-C 国内外对比分析（A 方案）`
- 交付面已收敛为飞书单通道；不再维护旧非飞书渠道
- 本地验证基线已随公开站 IA V2 第一批刷新到 `337 passed`
- 当前治理尾项已基本收口：repo-local watch runner 已打通，`candidate-updates.json` 接近空队列
- `renesas-blog` / `youtube-google-developers` / `youtube-nvidia` 已从活跃采集里降噪处理，等待稳定入口恢复后再启用
- 公开站 IA V2 第一批已完成并通过远端发布级确认：push run `25009309491` 成功，触发 commit `d743668`，远端产物推进到 `ba23ec5`
- 手动补触发 run `25009334909` 截至 2026-04-28 01:46 已通过 `analyze`，正在 `report`；下次接手先回看；它是重复确认 run，不阻塞 IA V2 第一批收口
- `2026-04-22` 上一轮远端 `Collect And Report` 已全链路通过（run `24762469538` / commit `46c47ef`）
- `2026-04-22` 已完成本地真实 Feishu 卡片主路径验证：`diagnose-delivery --mode full-report --send --channels feishu` 返回 `delivery_kind=card_success`
- `2026-04-22` 已把 `run-status` / delivery diagnose 的飞书交付信号补齐为 `card_success / text_fallback`
- `2026-04-24` 已确认最新远端 `Collect And Report` 成功（run `24892691284` / commit `a2f1455`）
- `2026-04-24` 已确认最新远端 `Delivery Canary` 成功（run `24864175041` / commit `780dcfd`）
- `2026-04-24` 已确认最新远端 `Source Reachability Canary` 成功（run `24864003455` / commit `780dcfd`）
- `2026-04-25` 已在本地真实 `auto` 轨验收 DeepSeek V4 路由，`summary/forecast` 输出与将要用于推送的摘要字段均为中文
- `2026-04-25` 已完成飞书运营台现有表的第一屏字段重排真实同步：`python -m auto_report.cli sync-feishu-ops-desk`
- 当前精确运行快照、主题数和风险等级仍以 `data/state/run-status.json` 为准

目前已经落地的关键收口：

- 飞书单通道交付策略
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

- `anthropic-news` 已完成收口：官方 RSS/feed 候选当前 404，保留远端已验证通过的官方 news listing 作为正式入口
- `P3-A` 已完成首轮发布级验收：
  1. 飞书静态卡片真实发送成功
  2. 文本 fallback 保留
  3. `diagnose-delivery --mode full-report --send --channels feishu` 已可做 Feishu-only 验证
- `P3-A` 当前交付面收口状态：
  1. `2026-04-22` 本地已实测卡片主路径命中：`delivery_kind=card_success`
  2. `run-status` / diagnose 输出已区分 `card_success / text_fallback`
  3. `2026-04-24` 最新远端 `Collect And Report` 已成功
  4. `2026-04-24` `Delivery Canary` 已在远端持续成功；本地 `2026-04-25` 已补中文输出约束，避免再次出现英文推送
- `P3-B` 第一版已经落地：
  1. `VS_AI 今日运营台` dashboard 已建成
  2. 四张表已建成：`治理总表` / `审批协作` / `交付验收` / `待应用变更`
  3. 已支持两条本地命令：
     - `python -m auto_report.cli sync-feishu-ops-desk`
     - `python -m auto_report.cli pull-feishu-ops-status`
  4. 已支持状态类回写：
      - `审批协作.status / note`
      - `交付验收.card_verified / fallback_observed / delivery_note`
  5. 第二轮 polish 已开始落地：
      - `审批协作.pending` 已中文化为 `待审批`
      - 视图过滤条件已与中文状态值对齐
      - `审批协作 / 交付验收` 可写字段已前置到左侧第一屏
      - 旧值 `待处理` 已纳入迁移兼容
      - 旧版英文表 / 仪表盘已支持删除优先、失败则改名停用，并已有 `test_lark_cli_sidecar.py` 覆盖
      - 轻自动化本阶段不新增，继续保留 `sync-feishu-ops-desk` / `pull-feishu-ops-status` 手动闭环
- 已完成主线：`P3-C 国内外对比分析（A 方案）`
  1. `P3-C-1`：source 标签层已完成：`region_scope / org_origin / tech_track / comparison_priority` 已进入 registry，覆盖 `frontier-ai / fpga / embedded / personal-hpc / compute-infra`
  2. `P3-C-2`：已在 summary payload 中新增 `comparison_brief.cn_highlights / intl_highlights / head_to_head / gaps / watchpoints`，Markdown 长报告完整展示，飞书文本 / 飞书卡片只消费前 1~2 条 `head_to_head`
  3. `P3-C-3`：已完成本地发布级验收、文档、运行态说明与生成产物清理；reviewed 样例中 `comparison_brief` 已可见
  4. P3-C 三阶段已完成；公开站 `https://wsysgz.github.io/VS_AI/` 的整理 / 优化进入下一步讨论，确认方案前不实施
  5. 后续再吸收事件级配对（C 方案）
- `OpenCLI` 侧车 pilot 继续延后，不与当前批次混做

最近可见的 source failure 示例：

补充状态（2026-04-18 之后继续接手时要记住）：

- P1 的核心工程目标已经基本收口，不再建议把 P1 当成长时间阻塞项
- P2 核心工程链路也已经基本收口：
  1. 双 AI 并存与 stage routing 已验证
  2. LiteLLM Gateway 已验证
  3. Langfuse tracing / prompt eval tracing / fallback / budget guardrail 已落地
- 下一阶段默认优先顺序：
  1. 先讨论公开站 `https://wsysgz.github.io/VS_AI/` 的整理 / 优化方案
  2. 方案确认后再实施公开站改造
  3. 实施前保留当前 Pages 结构，不做顺手优化
  4. `P3-B` 只保留小修、真实同步回归和交付前验证
  5. 持续观察 `openvino-blog`、`huggingface-blog`、`st-blog` 的超时/连通性噪音
  6. `P2.5 OpenCLI pilot` 继续留在 backlog
- 当前已确认的默认 AI 分工：
  - `analysis` -> DeepSeek V4 Pro
  - `summary` -> DeepSeek V4 Pro
  - `forecast` -> DeepSeek V4 Pro
  - `pre_filter` -> DeepSeek V4 Flash
  - `discovery` / `search` helper stage -> DeepSeek V4 Flash
- `build-discovery-search` 已可从关键词列表生成：
  - `out/discovery-search/discovery-search.json`
  - `out/discovery-search/discovery-search.md`
- `build-source-governance` 已会把 discovery/search 结果轻量挂到：
  - `discovery_search`
  - `official_feed_leads`
  - `rsshub_leads`
  - `changedetection_leads`
- `ops dashboard` 下一位接手时应重点看：
  - `Governance Priority Queue`
  - `Discovery Leads`
  - `Official Feed Leads`
  - `RSSHub Leads`
  - `changedetection Leads`
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
$env:AI_MODEL='deepseek-v4-flash'
$env:DEEPSEEK_API_KEY='<your-deepseek-key>'

# MiniMax-M2.7（通过 OpenAI-compatible 第三方入口）
$env:AI_PROVIDER='minimax_svips'
$env:AI_BASE_URL='https://api.svips.org/v1'
$env:AI_MODEL='MiniMax-M2.7'
$env:AI_API_KEY='<your-minimax-key>'

# LiteLLM Gateway（本地可选接入）
$env:AI_PROVIDER='litellm_proxy'
$env:AI_BASE_URL='http://127.0.0.1:4000'
$env:AI_MODEL='vs-ai-default'
$env:LITELLM_MASTER_KEY='sk-change-me'
```

注意：

- 当前已经支持按 `analysis / summary / forecast` 分阶段切换 provider。
- 当前建议默认分工：
  - `analysis` -> DeepSeek V4 Pro
  - `summary` -> DeepSeek V4 Pro
  - `forecast` -> DeepSeek V4 Pro
  - `pre_filter` -> DeepSeek V4 Flash
  - 未来 `discovery` / `search` helper stage -> DeepSeek V4 Flash
- 当前默认推荐已切到 DeepSeek V4：关键阶段用 `pro`，常规阶段用 `flash`。
- 预筛选阶段现已支持独立的 `PREFILTER_*` provider 设置。
- LiteLLM Gateway 首轮接入建议作为可选路径保留直连回退，不要一上来把所有环境强制切到 Gateway。
- 当前仓库内置的 LiteLLM provider 名称为 `litellm_proxy`，推荐配合 `config/litellm/litellm-config.example.yaml` 中的 alias 使用。
- Langfuse tracing 首轮接入采用 metadata-first：默认只上传 stage / provider / model / latency / token usage / status，不默认上传 prompt 和 response 正文。
- `P2-C` 已于 2026-04-20 完成本地与远端验证；当 Langfuse 可达时，`run-status.json` 现在会写入：
  - `tracing.enabled`
  - `tracing.trace_id`
  - `tracing.trace_url`
- `P2` 新增尾项（2026-04-21）：
  - `evaluate-prompts` 已接入 Langfuse tracing
  - `llm_client.py` 已支持：主 provider -> 备用 provider -> pipeline fallback 的两层降级
  - 已支持：
    - `BACKUP_AI_PROVIDER / BACKUP_AI_BASE_URL / BACKUP_AI_MODEL / BACKUP_AI_API_KEY`
    - `AI_MAX_STAGE_LATENCY_SECONDS / AI_MAX_STAGE_TOTAL_TOKENS`
    - 以及各 stage 的 `*_BACKUP_*`、`*_AI_MAX_*` 覆盖
  - `run-status.json` / `ai_metrics` 现在会额外记录：
    - `backup_stages`
    - `guardrail_stages`
    - 每个 stage 的 `attempts / backup_used / guardrail_reason / budget`

推荐默认分工：

```powershell
$env:ANALYSIS_AI_PROVIDER='deepseek'
$env:ANALYSIS_AI_BASE_URL='https://api.deepseek.com'
$env:ANALYSIS_AI_MODEL='deepseek-v4-pro'

$env:SUMMARY_AI_PROVIDER='deepseek'
$env:SUMMARY_AI_BASE_URL='https://api.deepseek.com'
$env:SUMMARY_AI_MODEL='deepseek-v4-pro'

$env:FORECAST_AI_PROVIDER='deepseek'
$env:FORECAST_AI_BASE_URL='https://api.deepseek.com'
$env:FORECAST_AI_MODEL='deepseek-v4-pro'

$env:PREFILTER_AI_PROVIDER='deepseek'
$env:PREFILTER_AI_BASE_URL='https://api.deepseek.com'
$env:PREFILTER_AI_MODEL='deepseek-v4-flash'

$env:DISCOVERY_AI_PROVIDER='deepseek'
$env:DISCOVERY_AI_BASE_URL='https://api.deepseek.com'
$env:DISCOVERY_AI_MODEL='deepseek-v4-flash'

$env:SEARCH_AI_PROVIDER='deepseek'
$env:SEARCH_AI_BASE_URL='https://api.deepseek.com'
$env:SEARCH_AI_MODEL='deepseek-v4-flash'
```

如果走 LiteLLM Gateway，推荐 alias 对应如下：

```powershell
$env:AI_PROVIDER='litellm_proxy'
$env:AI_BASE_URL='http://127.0.0.1:4000'
$env:LITELLM_MASTER_KEY='sk-change-me'

$env:ANALYSIS_AI_PROVIDER='litellm_proxy'
$env:ANALYSIS_AI_MODEL='vs-ai-analysis'

$env:SUMMARY_AI_PROVIDER='litellm_proxy'
$env:SUMMARY_AI_MODEL='vs-ai-summary'

$env:FORECAST_AI_PROVIDER='litellm_proxy'
$env:FORECAST_AI_MODEL='vs-ai-forecast'

$env:PREFILTER_AI_PROVIDER='litellm_proxy'
$env:PREFILTER_AI_MODEL='vs-ai-prefilter'
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
python -m auto_report.cli build-discovery-search --keywords config/source_discovery/keywords.txt
```

补充说明：

- `build-review-queue` 现在会同时输出：
  - `out/review-queue/review-issues.json`
  - `out/review-queue/source-lead-issues.json`
  - `out/review-queue/source-lead-review-status.json`
  - `out/review-queue/candidate-updates.json`
- `out/source-governance/changedetection-watch-registry.json`
- `out/source-governance/watch-run-results.json`
- 后者用于把 discovery / search / governance leads 转成人审 issue payload，并配合本地 watch runner 做治理收口
- 建议闭环：
  1. 看 `source-lead-issues.json`
  2. 在 `source-lead-review-status.json` 中把目标 lead 标成 `approved / rejected / deferred`
  3. 再跑一次 `build-review-queue`
  4. 用 `candidate-updates.json` 作为下一步 source/watch update 候选集
  5. 跑 `python -m auto_report.cli apply-source-updates`
  6. 跑 `python -m auto_report.cli run-watch-checks`
- 当前收尾阶段优先关注：`watch-run-results.json` 里的 `blocked / changed`

### 7.4 诊断交付

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli diagnose-delivery --mode canary
python -m auto_report.cli diagnose-delivery --mode canary --send
python -m auto_report.cli diagnose-delivery --mode full-report --send
python -m auto_report.cli diagnose-delivery --mode full-report --send --channels feishu
python -m auto_report.cli diagnose-delivery --mode full-report --send --channels feishu --require-feishu-card-success
python -m auto_report.cli sync-feishu-workspace --publication-mode reviewed
python -m auto_report.cli sync-feishu-ops-desk
python -m auto_report.cli pull-feishu-ops-status
```

补充原则：

- `sync-feishu-workspace` / `lark-cli` 是本地侧车，不是 GitHub Actions 主链依赖
- 远端 workflow 继续使用仓库原生 Feishu API 推送
- 若 `GITHUB_ACTIONS=true`，sidecar 会自动跳过
- 如果只想验证飞书卡片路径，优先用：
  - `python -m auto_report.cli diagnose-delivery --mode full-report --send --channels feishu --require-feishu-card-success`
- 远端 `Delivery Canary` 当前也已切到同一口径：只验证 Feishu 卡片主路径，`text_fallback` 不再算通过
- 如果要同步 / 回写 `P3-B` 运营台，优先用：
  - `python -m auto_report.cli sync-feishu-ops-desk`
  - `python -m auto_report.cli pull-feishu-ops-status`

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
$env:AI_DISABLE_LLM='true'
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
- reviewed 轨本地跑通；常规本地验收设置 `AI_DISABLE_LLM=true`，由 Codex 代替 DeepSeek 做验证审查
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
- 远端 workflow 触发后，不要卡在前台持续盯跑；记录 run 链接 / run id 后继续做本地工作，默认也不要求专门回头核对最终结果，除非用户明确要求或后续任务依赖它

建议优先触发 `Collect And Report`，并先把真实推送关掉：

```powershell
gh workflow run collect-report.yml --ref main -f push_enabled=false -f publication_mode=reviewed -f reviewer=manual-check -f review_note=post-push-verification
```

或者在 GitHub Actions UI 中手动点：

- Workflow：`Collect And Report`
- Branch：`main`
- `push_enabled = false`
- `publication_mode = reviewed`

### 8.4 如需回看远端结果

只有在用户明确要求、出现异常、或后续任务明确依赖远端结果时，再回来核对：

- 默认不要求一直前台 watch，也不要求专门补做一次“最终结果核对”
- `workflow-guard`、`test`、`collect`、`analyze`、`report` 都通过
- `deploy-pages`、`ops-dashboard`、`review-queue` 都通过
- 没有新出现的 reliability issue

## 9. 飞书单通道交付要点

当前仓库只维护飞书交付面：

- `run-once` 只读取 `FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_CHAT_ID`
- `diagnose-delivery --channels` 只接受 `feishu`
- 旧非飞书渠道已经从主链、workflow、配置和文档中移除
- 发布级交付验证继续使用：

```powershell
python -m auto_report.cli diagnose-delivery --mode full-report --send --channels feishu --require-feishu-card-success
```

判定标准：

- `delivery_kind=card_success` 才算飞书卡片主路径通过
- `delivery_kind=text_fallback` 说明卡片失败后走了飞书文本 fallback，诊断命令在 `--require-feishu-card-success` 下必须失败
- `data/state/run-status.json` 中的 `delivery_results.channels` 只应出现 `feishu`

## 10. 最容易踩的坑

- 忘记设置 `$env:PYTHONPATH='src'`
- 只看 Actions 颜色，不看 `run-status.json`
- 改了 workflow 却没 push 就去手动 dispatch
- 把候选 feed / RSSHub 链接直接当正式 source，不先验证真实可用性
- 看到 `candidate-updates.json` 就直接改配置，不先看 `apply_ready / blocking_reason / validation_mode`
- 把飞书文本 fallback 误认为卡片主路径成功
- 修改状态 schema 但没同步 dashboard / 页面 / 测试
- 把信息性诊断误记入 `source_health`
- 把远端 workflow 当成必须前台盯到结束、或每次都必须专门补做最终结果核对

## 10.5 建库 / 收口经验

- 先把 artifact 铺起来，再决定是否进入主链；`source-governance.json`、`source-lead-issues.json`、`candidate-updates.json` 都是这样长出来的
- 对来源收口不要执着于“必须切到 feed”；`anthropic-news` 的正确收口是 validated listing，而不是一个返回 404 的伪 feed
- 远端验证真正依赖的是“远端 main 上的 workflow 文件是不是最新”，不是本地工作区看起来有没有改好
- 本地 sidecar（如 `lark-cli`）只做本地验证、美化输出、协作同步，远端主链继续走仓库原生 Feishu API
- 人工审批流要走完整：`source-lead-issues.json -> source-lead-review-status.json -> candidate-updates.json`
- 预算/降级策略最好放在同一层：provider fallback 放在 `llm_client.py`，非 AI fallback 继续留在 pipeline 层，不要混成一团
- `P3-B` 当前已落地的最小可用闭环是：
  - `python -m auto_report.cli sync-feishu-ops-desk`
  - 在飞书里改 `审批协作 / 交付验收` 的状态字段
  - `python -m auto_report.cli pull-feishu-ops-status`
- `P3-B` 字段交互当前已确认：
  - `审批协作.状态` -> 单选
  - `交付验收.卡片已确认` -> 复选框
  - `交付验收.发现回退` -> 复选框
- 飞书 API 当前 profile 下的已知限制：
  - 可能不能删除旧表 / 旧 dashboard
  - 可能不能删除 dashboard block
  - 可能不能强制设置所有视图可见字段顺序
  - 所以当前更稳的策略是：删不掉就改名成“旧版…（停用）”
- 项目收尾时优先清理本地临时目录：
  - `.codex-pytest-temp*`
  - `.codex-tmp`
  - `.pytest_cache`
  - `.pytest-codex-*`
  - `.pytest-tmp`
  - `codex_pytest_temp`
  - `pytest-tempdir*`
- 不要把以下目录当成“临时垃圾”直接删：
  - `data/`
  - `docs/`
  - `out/`
  - `docs/superpowers/`
- 如果这类本地临时目录删除时遇到 `Access denied`，优先判断是不是测试进程残留或 ACL 异常；不要为了清理临时目录去误删正式交付目录

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
- 当前优先级已转到：公开站 IA V2 第一批收口；`P3-C-1 / P3-C-2 / P3-C-3` 已完成；repo 内原生 watch runner 只保留例行观察
- 运行态真相文件是 data/state/run-status.json
- 手动触发 workflow 前必须先 push
- 直接在 main 上工作，不创建功能分支
```

## 12.5 下次上手最短路径

如果下一位只想最快恢复推进节奏，按这个顺序：

1. `git status --short`
2. `git log --oneline -5`
3. 读 `交接备忘录.md`
4. 读 `AI对接手册.md`
5. 看 `data/state/run-status.json`
6. 看 `out/source-governance/source-governance.json`
7. 看 `out/review-queue/source-lead-review-status.json`
8. 当前默认进入公开站 IA V2 第一批收口 / 发布确认；不要回头重做 `P3-C-1 / P3-C-2 / P3-C-3`
- 旧非飞书渠道不再作为当前优化对象

## 12. AI 接手后的首小时清单

建议第一小时只做下面这些高价值动作：

1. 确认仓库干净、确认最近提交方向
2. 读取 `run-status.json` 和 `source-governance.json`
3. 判断当前工作属于：文档、来源治理、workflow、推送诊断、页面输出中的哪一类
4. 如果是代码或配置改动，先定义本地验收命令
5. 完成本地验证后再考虑 `push` 与远端 dispatch

如果你是临时接手，不确定该优先干什么，默认优先：

1. P3-A：飞书推送界面优化尾部小修（`Delivery Canary` 已升级为飞书卡片主路径 canary）
2. P3-C-2：comparison brief 与交付消费（已完成）
3. P3-C-3：验收、文档、发布收口（已完成）
4. 公开站 IA V2 第一批已完成并通过远端 push run `25009309491` 确认
5. 下次先回看手动补触发 run `25009334909`，只记录结果；若失败先看失败 job，不回滚 IA V2 第一批
6. 后续再评估 IA V2 第二批：来源总览页、赛道/来源交叉视图、移动端筛选体验
