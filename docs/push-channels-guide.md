# Push Channels Guide

保持每天 07:00 报告送达三大渠道（WeChat/PushPlus、Telegram、Feishu）是本系统的核心体验。本指南说明每条通道的配置、输出格式和验证方式。

## 每日推送策略

- 定时 workflow `Collect And Report` (`.github/workflows/collect-report.yml`) 的 `schedule` 触发会按北京时间 07:00 执行一次完整 pipeline。
- 该 workflow 生成文件后依次调用 PushPlus、Telegram、Feishu，默认只推送一次，`push` 型 trigger 仅用于 CI 验证。
- `AUTO_PUSH_ENABLED=true` 时，dispatch/cron 自动触发时默认打开推送；如需暂时禁用，直接把环境变量设为 `false`，或在 GitHub 手动触发时将 workflow input `push_enabled=false`。
- GitHub 仓库需要把 `Workflow permissions` 设为 `Read and write permissions`，否则 `report` 与 `deploy-pages` 不能自动回写结果。

## PushPlus (WeChat 短摘要)

- 环境变量：`PUSHPLUS_TOKEN`、`PUSHPLUS_CHANNEL`（默认 `clawbot`）、`PUSHPLUS_BASE_URL`、可选 `PUSHPLUS_SECRETKEY`。
- 消息内容：`pushplus` render 输出 `txt` 短摘要 + GitHub 详情链接；详见 `integrations/pushplus.py`。
- 验证方式：先运行 `python -m auto_report.cli diagnose-delivery` 确认配置生效，再运行 `python -m auto_report.cli diagnose-delivery --send` 或 `python -m auto_report.cli run-once`；重复验证请观察 `data/state/run-status.json` 中 `delivery_results.channels.pushplus`。
- 常见问题：token 失效/通道被禁用会在 `pushplus` 日志中记录失败详情；如果配置了错误的 `PUSHPLUS_SECRETKEY`，PushPlus 通常会返回 `code=903`。

## Telegram (完整报告)

- 环境变量：`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、可选 `TELEGRAM_API_BASE_URL`。
- 系统自动将完整纯文本报告拆成 `<=4096` 字符段落并顺序发送，确保最终消息附带 GitHub 报告链接。
- 验证方式：运行 `python -m auto_report.cli diagnose-delivery --send` 或 `python -m auto_report.cli run-once`，观察目标群/频道是否接收完整文本；`run-status.json` 中看 `delivery_results.channels.telegram`。
- 失败排查：检查 bot 是否被禁用、chat_id 是否正确、本机是否能连通 `api.telegram.org`。如果本机网络受限，可改用 `TELEGRAM_API_BASE_URL` 代理，或以 GitHub Actions 回写的 `run-status.json` 作为远端验收证据。

## Feishu (完整报告)

- 环境变量：`FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CHAT_ID`、可选 `FEISHU_API_BASE_URL`。
- Feishu 机器人通过 `tenant_access_token` + `im/v1/messages` API 发送完整纯文本正文；格式在 `integrations/feishu.py` 中可调。
- 验证方式：同样依赖 `python -m auto_report.cli diagnose-delivery --send` 或 `python -m auto_report.cli run-once` → 查收飞书群/应用 → 检查 `run-status.json` 中 `delivery_results.channels.feishu`。
- 失败排查：确认机器人被添加到 chat 中且有“发送消息”权限；如果飞书拒绝请求，可在日志中看到 `msg` 与 `code`。

## 观测与复核

- `data/state/run-status.json` 记录所有通道的 `delivery_results`，其中 `successful_channels`、`failed_channels`、`skipped_channels` 是验收三端是否真正送达的第一手日志。
- 当一个 channel 缺少凭据时，系统会跳过相关推送并在 run-status 里写入 `skipped`（例如缺少 `PUSHPLUS_TOKEN` 时会提示“PushPlus not configured”）。
- 在 GitHub Actions 中，优先查看 `report` job 是否成功，再读取远端 `data/state/run-status.json`；这样可以区分“消息送达失败”和“后续提交 Pages 失败”。

## 备用手段

- 如果必须临时停止 Telegram/Feishu，只要在 `.env` 中删除对应 token 即可，其他通道不会受影响。
- PushPlus 除了 short text 还会附带 GitHub 报告链接，便于手动回溯；因此即使 Telegram/Feishu 没成功，短摘要仍能确保有人看到 Link。
