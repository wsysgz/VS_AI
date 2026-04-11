# Push Channels Guide

保持每天 07:00 报告送达三大渠道（WeChat/PushPlus、Telegram、Feishu）是本系统的核心体验。本指南说明每条通道的配置、输出格式和验证方式。

## 每日推送策略

- 定时 workflow `Collect And Report` (`.github/workflows/collect-report.yml`) 的 `schedule` 触发会按北京时间 07:00 执行一次完整 pipeline。
- 该 workflow 生成文件后依次调用 PushPlus、Telegram、Feishu，默认只推送一次，`push` 型 trigger 仅用于 CI 验证。
- `AUTO_PUSH_ENABLED=true` 时，dispatch/cron 自动触发时默认打开推送；可通过 `--push-enabled=false` 或 GitHub workflow input `push_enabled=false` 暂时禁用。

## PushPlus (WeChat 短摘要)

- 环境变量：`PUSHPLUS_TOKEN`、`PUSHPLUS_CHANNEL`（默认 `clawbot`）。
- 消息内容：`pushplus` render 输出 `txt` 短摘要 + GitHub 详情链接；详见 `integrations/pushplus.py`。
- 验证方式：运行 `auto_report.cli run-once` → 检查 WeChat 是否收到“每日综合报短摘要”；重复验证请观察 `data/state/run-status.json` 中 `pushplus.status` 字段。
- 常见问题：token 失效/通道被禁用会在 `pushplus` 日志中记录 HTTP 401/403，推送逻辑会继续但记录 `pushes` 中的 `failed` 条目。

## Telegram (完整报告)

- 环境变量：`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`。
- 系统自动将完整 Markdown 报告拆成 `<=4096` 字符段落并顺序发送，确保最终一条消息附带 GitHub 报告链接。
- 验证方式：运行 `python -m auto_report.cli run-once`，观察目标群/频道是否接收多段文本；`run-status.json` 中有 `telegram.status` 与 `telegram.chunks`。
- 失败排查：检查 bot 是否被禁用、chat_id 是否正确，或是否有网络限制；可在 `tests/test_telegram.py` 中找到模拟格式参考。

## Feishu (完整报告)

- 环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`。
- Feishu 机器人通过 Webhook 接收内容，默认发送完整正文及附件链接；格式在 `integrations/feishu.py` 中可调。
- 验证方式：同样依赖 `run-once` → 查收飞书群/应用 → 检查 `run-status.json` 中的 `feishu.status`。
- 失败排查：确认机器人被添加到 chat 中且有“发送消息”权限；如果飞书拒绝请求，可在日志中看到 `msg` 与 `code`。

## 观测与复核

- `data/state/run-status.json` 记录所有通道的 `status` 与 `failures`，是验证每次 run 是否完成推送的第一手日志。
- 当一个 channel 缺少凭据时，系统会跳过相关推送并在 run-status 里写入 `skipped`（例如缺少 `PUSHPLUS_TOKEN` 时会提示“PushPlus not configured”）。
- 日志中 `pushes` 数组按顺序记录每个通道执行结果；在 GitHub Actions 的 `render-and-push` job 也会输出类似细节。

## 备用手段

- 如果必须临时停止 Telegram/Feishu，只要在 `.env` 中删除对应 token 即可，其他通道不会受影响。
- PushPlus 除了 short text 还会附带 GitHub 报告链接，便于手动回溯；因此即使 Telegram/Feishu 没成功，短摘要仍能确保有人看到 Link。
