# 技术指导手册

## 项目定位

这是一个“本地优先 + GitHub 可部署”的定时情报采集与自动快报框架，目标是让后续 AI 或开发者可以在这个基础上持续扩展，而不是每次重搭。

当前主仓库是 `https://github.com/wsysgz/VS_AI`，默认本地工作目录是 `D:\GitHub\auto`。

当前默认远端是 SSH：

- `origin = git@github.com:wsysgz/VS_AI.git`
- 验证命令：`ssh -T git@github.com`

如果后续 AI 接手，优先沿用当前 SSH 方式，不要为了“先跑起来”再切回 HTTPS。

## 给后续 AI / 开发者的规则

- 先读取仓库根目录 `AGENTS.md`，再开始动代码。
- 优先在 `D:\GitHub\auto` 主工作区开发；如果要用 worktree，最终仍要回到主工作区复核、合并、推送。
- 先改 `config/sources/*.yaml`，再决定是否需要改采集代码。
- 领域规则尽量放在 `src/auto_report/domains/`，不要散落到各处。
- 归档输出统一留在 `src/auto_report/outputs/`。
- 推送和模型供应商适配器统一放在 `src/auto_report/integrations/`。
- 博客同步必须保持“可选扩展”，不要反向耦合进 `run-once`。
- GitHub Actions 主工作流是 `.github/workflows/collect-report.yml`，当前支持 `push + workflow_dispatch + schedule` 三种触发。
- 官方用户通知目前只保留北京时间 `07:00` 的综合总报。
- `push` 和 `workflow_dispatch` 触发默认用于验证与归档，默认 `AUTO_PUSH_ENABLED=false`。
- `workflow_dispatch` 可通过输入参数显式打开推送，用于仓库侧受控验证。
- PushPlus 当前优先走 `clawbot` 渠道，并发送 `txt` 短摘要 + GitHub 详情链接。
- Telegram 当前作为可选同步通道，发送完整报告正文，并自动按 `4096` 字符上限切分为多条纯文本消息，最后附 GitHub 详情链接。
- 如果后续要回退到其他渠道，必须显式配置，不要做静默回退。
- `collect-report.yml` 已对 `data/**` 使用 `paths-ignore`，后续如果继续扩展自动提交范围，必须先检查是否会造成工作流自触发回环。
- 当前 GitHub Actions 主任务 `timeout-minutes: 25`，保持每天自动运行总时长不超过 `60` 分钟。

## 推送通道边界

### PushPlus ClawBot

- 当前策略是把它视为“微信短摘要通道”，不承载完整长文。
- 统一使用 `txt` 模板，正文里保留简短摘要和 GitHub 详情链接。
- 这是为了降低微信侧图文/上下文限制带来的不稳定性。
- 如果用户反馈收不到消息，优先检查：
  - PushPlus 是否仍可正常推送
  - ClawBot 会话是否仍处于激活状态
  - Token 是否有效

### Telegram Bot

- 当前策略是把它视为“完整报告通道”。
- 不依赖 GitHub 风格 Markdown 渲染，统一按纯文本发送，减少格式解析失败。
- 如果报告超过单条消息限制，就自动拆成多条消息顺序发送。
- 需要用户先与 bot 建立私聊会话，否则即使 token/chat id 正确，也可能无法完成首次送达。

## 推荐验证顺序

```powershell
python -m pytest -q
python -m auto_report.cli run-once
git status --short
git remote -v
ssh -T git@github.com
```

如果修改了通知逻辑，再额外核对：

- `data/reports/latest-summary.md`
- `data/state/run-status.json`
- 微信 / Telegram 的实际展示效果

## 本轮已沉淀的关键决策

- 仓库接管方式以现有 SSH 远端为准，这是当前最快且最稳定的路径。
- 日常对用户只保留 `07:00` 的一条综合总报，不再拆成多条每日自动推送。
- ClawBot 只发短摘要，Telegram 发完整正文。
- 先本地跑通，再推送到 GitHub Actions 自动验证与归档。

## 当前主要命令

```powershell
python -m auto_report.cli run-once
python -m auto_report.cli render-report
```

## 当前最安全的扩展顺序

1. 增加周报
2. 增加月报
3. 继续补真实 RSS / API / 页面采集器
4. 给 GitHub 源增加更细的查询策略
5. 把 DeepSeek 真正用于候选主题摘要和趋势整理
6. 扩充 `run-status.json` 与 `dedup-index.json`
7. 优化版面和阅读体验
8. 增加博客同步接口桩

## 当前已知限制

- 真实来源已经接入，但还属于第一批基础适配器
- `backfill` 还不是完整历史回放引擎
- 当前预测与分析仍以规则摘要为底，DeepSeek 是增强层，不是唯一依赖
