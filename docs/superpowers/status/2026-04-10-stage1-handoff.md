# 2026-04-10 第一轮本地升级交接

## 1. 本文用途

这份文档用于在对话清除、记忆消除或更换接手人后，快速恢复 `VS_AI` 当前阶段状态。

建议新的接手会话优先阅读：

1. 本文
2. `docs/superpowers/specs/2026-04-10-precision-source-ai-pipeline-design.md`
3. `docs/superpowers/plans/2026-04-10-precision-source-ai-pipeline.md`
4. `README.md`

## 2. 当前总状态

用户原始 9 条计划中，本轮已经完成并落地的是前两部分：

1. 已完成：完整阅读并升级工作区项目，建立仓库内置 AI 预读文件、精选信息源、分阶段 AI 管线、本地优先验证链路
2. 已完成：保持每天北京 `07:00` 左右推送快报，双通道仍为微信 `PushPlus/ClawBot` + `Telegram`

当前尚未展开的下一轮重点是：

3. 优化快报界面，不只是纯文字
4. 继续扩大信息源，但坚持“稳准少而精”
5. 继续增强 AI 的分析 / 总结 / 预测能力

## 3. 本轮已落地的关键成果

### 3.1 仓库内置 AI 预读文件

三份用户提供的方法论文档已经复制进仓库，并在运行时由系统自动读取：

- `config/ai_reading/analysis-before.md`
- `config/ai_reading/summary-before.md`
- `config/ai_reading/forecast-before.md`

这意味着后续调用的 AI 不再依赖桌面路径，电脑关机也不会影响 GitHub Actions 或其他机器继续运行。

### 3.2 信息源与去噪

已完成第一轮“少而精”精选源改造：

- `OpenAI News RSS`
- `Hugging Face Blog RSS`
- `Anthropic Newsroom`
- `DeepSeek Change Log / News`
- `Moonshot 官方博客`
- 精选 GitHub 仓库观察列表

已修复的问题：

- 失效的 `DeepSeek` / `Moonshot` 页面入口
- Anthropic 标题被“日期 + 分类 + 摘要”污染
- RSS 中低价值条目，如 `contest` / `terms & conditions`

### 3.3 分阶段 AI 管线

当前主流程已经变为：

`精选采集 -> 去噪过滤 -> 主题归并 -> 分析 -> 总结 -> 预测 -> 微信/Telegram 渲染 -> 归档/推送`

对应关键代码：

- `src/auto_report/pipeline/prompt_loader.py`
- `src/auto_report/pipeline/topic_builder.py`
- `src/auto_report/pipeline/ai_pipeline.py`
- `src/auto_report/pipeline/source_filters.py`

### 3.4 真实 AI 执行加固

为避免本地和 GitHub Actions 因真实 AI 全量串行调用而超时，已经补上：

- 默认 `AI_MAX_ANALYSIS_TOPICS=6`
- 只让优先级最高的主题进入真实 AI 分析
- 对 `analysis / summary / forecast` 返回结构做字段校验
- 返回结构不合规时明确回退，不再把错误 JSON 误判为 `ok`

配置入口：

- `.env.example`
- 本地 `.env`
- `src/auto_report/settings.py`

## 4. 本轮验证结果

在 `main` 上已经完成的关键验证：

- `python -m pytest -q`
  - 结果：`36 passed, 8 warnings`
- `python -m auto_report.cli run-once`
  - 结果：退出码 `0`

关键运行结果：

- `data/state/run-status.json` 中：
  - `analysis = ok`
  - `summary = ok`
  - `forecast = ok`

本地实跑时，微信和 Telegram 推送链路也已成功跑通一次。

说明：

- 只要本地 `.env` 中保留有效配置，再次本地执行 `run-once` 时，可能会再次触发真实推送
- 如果只想验证生成，不想打扰手机通道，请先把 `AUTO_PUSH_ENABLED=false`

## 5. 密钥与配置约定

### 5.1 `DEEPSEEK_API_KEY`

真实 `DEEPSEEK_API_KEY` 已经配置在本地 `.env` 中，供当前机器继续接手时直接使用。

安全约定：

- 真实 Key 只保留在本地 `.env` 和 GitHub Actions Secrets
- 不要把真实 Key 写入仓库 Markdown、代码文件或 git 提交

### 5.2 当前建议配置

最重要的本地配置项：

- `DEEPSEEK_API_KEY`
- `AI_MODEL=deepseek-chat`
- `AI_MAX_ANALYSIS_TOPICS=6`
- `PUSHPLUS_TOKEN`
- `PUSHPLUS_CHANNEL=clawbot`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 6. 当前代码与仓库状态

第一轮本地升级代码已经：

- 本地合并回 `main`
- 推送到远端 `origin/main`

可将当前状态理解为：

- 第一轮“1 + 2”部分已经完成
- 代码、文档、测试、真实 AI 执行链路都已经打通
- 下一轮应从“3 / 4 / 5”部分继续，不需要重做这一轮基础建设

## 7. 下一轮建议直接承接的任务

下一轮建议按下面顺序继续：

1. 第 3 部分：优化快报界面与表现形式
   - 目标不是网页大改版，而是在微信 / Telegram / Markdown 中先做更强的阅读体验和版式层次
2. 第 4 部分：继续扩源
   - 继续坚持“少而精”
   - 优先补国内外高价值官方源、研究源、基础设施源
3. 第 5 部分：继续增强 AI 能力
   - 提高证据利用率
   - 提高低证据主题的降权与回退质量
   - 强化总结 / 预测的稳定结构与可解释性

## 8. 新会话接手建议

如果后续在新会话继续：

1. 先读取本文
2. 再读取设计文档和计划文档
3. 再检查 `git status`
4. 再决定是否直接进入第二轮（第 3 / 4 / 5 部分）

特别注意：

- 主工作区可能存在本地生成的 `data/` 变化，这是正常现象
- 不要随意回退用户未说明要删除的本地产物
- 若重新本地执行 `run-once`，默认可能会触发真实推送，先确认 `.env` 中的推送开关
