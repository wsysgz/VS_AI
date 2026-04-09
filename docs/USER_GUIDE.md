# 用户操作手册

## 1. 这个项目能做什么

这个项目当前可以：

- 每天北京时间 `07:00` 自动生成并推送 `1` 条综合总报
- 同时生成 `AI / 大模型 / Agent` 与 `AI × 电子信息` 两份领域快报供归档
- 把报告留档到本地 `data/` 目录
- 在 GitHub Actions 中执行并保存产物
- 通过 PushPlus 把摘要推送到微信，当前优先尝试 `ClawBot`
- 可选同步到 Telegram Bot，并发送完整报告正文

## 2. 本地运行

### 第一步：进入项目目录

项目根目录是：

`D:\GitHub\auto`

### 第二步：安装依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

也可以直接运行：

```powershell
.\scripts\bootstrap.ps1
```

### 第三步：配置本地密钥

把 `.env.example` 复制为 `.env`，然后填写：

- `DEEPSEEK_API_KEY`
- `PUSHPLUS_TOKEN`
- `PUSHPLUS_CHANNEL=clawbot`
- `REPORT_REPO_URL=https://github.com/wsysgz/VS_AI`
- `AI_MODEL`

如果你也想同步到 Telegram，再额外填写：

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

如果你暂时还没有 DeepSeek Key，也可以先不填，系统会用规则摘要模式继续运行。

### 第四步：本地执行一次

```powershell
python -m auto_report.cli run-once
```

建议默认开发流程：

1. 先在 `D:\GitHub\auto` 本地修改
2. 本地执行 `python -m auto_report.cli run-once`
3. 确认输出与推送符合预期
4. 再推送到仓库触发 GitHub Actions 自动验证和归档

### 第五步：检查输出结果

重点看这些文件：

- `data/reports/latest-summary.md`
- `data/reports/latest-summary.json`
- `data/reports/latest-ai-llm-agent.md`
- `data/reports/latest-ai-x-electronics.md`
- `data/state/run-status.json`

## 3. 部署到 GitHub

### 第一步：创建 GitHub 仓库

在 GitHub 上新建一个仓库，然后把当前项目推上去。

### 第二步：配置 GitHub Actions Secrets

打开：

`仓库 Settings -> Secrets and variables -> Actions`

至少新增下面这些：

- `DEEPSEEK_API_KEY`

如果你希望手机收到推送，再额外新增：

- `PUSHPLUS_TOKEN`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

说明：

- `DEEPSEEK_API_KEY` 建议配置，这样 GitHub 上生成的报告会带 AI 分析增强。
- `PUSHPLUS_TOKEN` 是微信推送所需的 Token。
- `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 配齐后，可同步推送到 Telegram。
- `GITHUB_TOKEN` 不需要手动新建，GitHub Actions 会自动提供默认值。

### 第三步：启用 GitHub Actions

进入仓库的 `Actions` 页面，如果 GitHub 提示确认，点击允许工作流运行。

### 第四步：手动触发第一次执行

打开工作流：

`Collect And Report`

点击：

`Run workflow`

后续只要你再向 `main` 分支推送代码，`Collect And Report` 也会自动执行一次，不需要每次手动点。

说明：

- 每天北京时间 `07:00` 的 `schedule` 运行，是正式自动推送到微信的那一轮
- 推送到 `main` 触发的运行，默认用于验证和归档，不主动发送微信消息
- 手动 `Run workflow` 时，可以按需要显式打开推送，用来做一次受控测试
- 主工作流 `timeout-minutes: 25`，因此日常自动运行不会超过 `60` 分钟

### 第五步：核对执行结果

检查这几项：

- 工作流日志是否成功结束
- 是否生成了名为 `auto-report-data` 的 artifact
- 仓库里的 `data/` 文件是否更新
- 如果这是北京时间 `07:00` 的定时运行，且配置了 `PUSHPLUS_TOKEN`，手机是否收到 PushPlus 短摘要
- 如果配置了 Telegram，Telegram 对话是否收到完整报告正文 + GitHub 详情链接

## 4. 手动补生成

如果你想手动补跑一轮，可以使用工作流：

`Backfill Report`

当前第一版的 `Backfill Report` 还是偏“重新渲染”模式，完整历史补跑会在下一批增强里继续补上。

## 5. 修改关注领域

如果你想调整领域关键词，修改：

- `config/domains/ai-llm-agent.yaml`
- `config/domains/ai-x-electronics.yaml`

如果你想增加或删减信息源，修改：

- `config/sources/rss.yaml`
- `config/sources/github.yaml`
- `config/sources/websites.yaml`

## 6. 后续扩展方向

当前项目已经为这些方向预留了扩展空间：

- 周报
- 月报
- 更多信息源
- 更强的分析能力
- 版面与阅读体验优化

## 7. Telegram 设置说明

如果你已经从 `@BotFather` 获得：

- Bot Token
- Chat ID

那么项目里需要配置的就是：

- 本地 `.env`
  - `TELEGRAM_BOT_TOKEN=你的 Bot Token`
  - `TELEGRAM_CHAT_ID=你的 Chat ID`
- GitHub Secrets
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`

只要 Bot 已经和你的账号建立过会话，之后定时运行就能把短摘要推过去。

现在 Telegram 的默认行为是：

- 发送完整报告正文
- 如果太长，会自动拆成多条纯文本消息
- 最后附 GitHub 详情链接

首次配置时建议手动做这几步：

1. 在 Telegram 中打开 bot 对话
2. 先发送一次 `/start`
3. 本地运行 `python -m auto_report.cli run-once`
4. 确认 Telegram 是否收到完整报告

## 8. 微信 ClawBot 说明

当前微信侧默认使用 PushPlus 的 `ClawBot` 渠道。

为了提高稳定性，项目默认只向微信发送：

- 短摘要
- GitHub 详情链接

如果微信侧后续收不到消息，优先检查：

1. PushPlus Token 是否仍有效
2. ClawBot 会话是否仍处于可接收状态
3. 是否需要重新激活 / 刷新会话
