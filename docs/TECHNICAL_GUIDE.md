# VS_AI 技术指南

本指南记录项目的关键配置、AI 供应商切换和降级机制，帮助工程人员掌握哪组环境变量驱动整个 pipeline。

## 环境变量概览

| 变量 | 默认值 | 说明 | 是否必须 |
|------|--------|------|-----------|
| `DEEPSEEK_API_KEY` | *(空)* | DeepSeek 的 API key；负责 AI 分析、总结、预测。 | ✅ |
| `OPENAI_API_KEY` | *(空)* | 可作为 `AI_PROVIDER=openai` 时的备用密钥。 | ✅（当 `AI_PROVIDER=openai`） |
| `AI_PROVIDER` | `deepseek` | 选择 `deepseek` 或 `openai`，控制 `integrations/llm_client.call_llm` 调用哪个适配器。 | ✅ |
| `AI_BASE_URL` | *(空)* | 覆盖默认的服务端点（如 `https://api.deepseek.com`），用于私有部署或代理。 | 可选 |
| `AI_MODEL` | `deepseek-chat` | DeepSeek/OpenAI 请求使用的模型名称。 | 可选 |
| `AI_TEMPERATURE` | `0.2` | 指定生成温度（控制创造性）。 | 可选 |
| `AI_MAX_ANALYSIS_TOPICS` | `6` | 每轮最多送给 AI 处理的主题数，用于平衡成本与时间。 | 可选 |
| `AUTO_PUSH_ENABLED` | `true` | 控制是否让 `Collect And Report` workflow 在 schedule/dispatch 触发推送。 | 可选 |
| `AUTO_TIMEZONE` | `Asia/Shanghai` | 时区，Dispatcher 用来计算北京时间 07:00。 | 可选 |
| `PUSHPLUS_TOKEN`, `PUSHPLUS_BASE_URL`, `PUSHPLUS_SECRETKEY`, `PUSHPLUS_CHANNEL` | *(空)* / `https://www.pushplus.plus` / *(空)* / `clawbot` | PushPlus 令牌、端点、可选签名 secret 和通道名。 | 可选 |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_API_BASE_URL` | *(空)* / *(空)* / `https://api.telegram.org` | Telegram bot、目标 chat 与可覆盖的 API 域名。 | 可选 |
| `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_CHAT_ID`, `FEISHU_API_BASE_URL` | *(空)* / *(空)* / *(空)* / `https://open.feishu.cn` | 飞书机器人凭据与 API 域名。 | 可选 |
| `DELIVERY_REQUEST_TIMEOUT` | `20` | 三端推送 HTTP 超时时间（秒）。 | 可选 |

更多变量（`GITHUB_TOKEN`、`REPORT_REPO_URL` 等）也可以在 `.env.example` 找到，真正上线前务必确认 `.env` 与 GitHub Secrets 中的名称一致。

## AI 配置

- `DEEPSEEK_API_KEY`：默认 DeepSeek 的 API key，控制 AI 分析、总结、预测。
- `AI_PROVIDER`：选择 `deepseek` 或 `openai`，决定 `integrations/llm_client.call_llm` 走哪套适配器。
- `AI_BASE_URL`：覆盖默认服务端点，适用于代理或私有部署。
- `AI_MODEL`：指定 DeepSeek/OpenAI 请求使用的模型名称。
- `AI_MAX_ANALYSIS_TOPICS`：限制每轮交给 AI 的主题数量，默认值为 `6`。

如果没有 AI Key，系统必须回退到规则摘要模式而不是中断。

## 交付与仓库设置

1. `Actions > General > Workflow permissions` 必须设置为 `Read and write permissions`，否则 workflow 无法自动提交 `data/**` 与 `docs/**`。
2. `PUSHPLUS_SECRETKEY` 只有在 PushPlus 端确实启用了配套签名时才应填写；错误的 secret 会把 token 签坏，直接导致 `code=903`。
3. 如果本机网络无法直连 Telegram，可通过 `TELEGRAM_API_BASE_URL` 指向代理域名；默认仍为 `https://api.telegram.org`。
4. `diagnose-delivery` 与 `run_once` 都会把逐通道结果写入 `data/state/run-status.json > delivery_results`，这是判断送达是否真实成功的权威字段。

## AI 提供商切换与降级机制

1. 默认情况下 `AI_PROVIDER=deepseek`，`integrations/llm_client.call_llm` 会用 `DEEPSEEK_API_KEY` 与 `AI_BASE_URL`/`AI_MODEL` 组合向 DeepSeek 发送请求。
2. 如果需要切换到 OpenAI，将 `AI_PROVIDER=openai` 并提供 `OPENAI_API_KEY`：客户端会在内部选择 `deepseek` 或 `openai` 适配器，仍然尊重 `AI_MODEL`（可换成 `gpt-4o-mini` 等）。
3. `AI_MAX_ANALYSIS_TOPICS` 为 6 时意味着 pipeline 只把优先级最高的 6 个主题送到 AI，避免耗时过长。调整此值需对分析时长和成本进行权衡。
4. 如果 `DEEPSEEK_API_KEY`（或其他 key）缺失，或 DeepSeek/OpenAI 多次调用失败，管线会降级为“规则摘要”模式：AI 阶段跳过，仍然写出结构化主题、要点和预测，并继续推送；日志会提醒 `rule summary` 被启用。
5. `AI_BASE_URL` 可指向私有部署或旁路代理，务必确认该主机可访问，且符合 TLS 证书标准，否则流程会落到第四步的规则摘要模式。

`settings.py` 会把这些变量封装进 `Settings` dataclass，`ai_pipeline.py` 里的 `run_staged_ai_pipeline()` 依赖 `StageTimer` 记录每一步，`integrations/llm_client.py` 负责低耦合的 API 调用；修改配置后记得同步更新这些文件。

## 校验与调试建议

- `.env.example` 给出了所有可配置字段。任何新增字段都要在 `README`/`USER_GUIDE`/`docs/push-channels-guide.md` 中提及，确保有人知道它们的作用。
- 运行 `python -m auto_report.cli run-once` 时，`data/state/run-status.json` 中的 `llm_status` 和 `errors` 字段会显示 AI 调用是否成功。若看到 `use_rule_summary: true`，说明 DeepSeek/API key 未配置或请求被拒绝。
- 使用 `python -m auto_report.cli analyze-only` + `--dry-run`（如需要）可以单独验证 AI 阶段，不必每次都跑完整 pipeline。
- 若需要在 CI 之外手动触发，确认 `.github/workflows/collect-report.yml` 的 `push_enabled` input 与 `AUTO_PUSH_ENABLED` 保持一致，以免自动推送被关闭。

## 附录

- 若需排查 `DeepSeek` 连接，检查 `integrations/llm_client.py` 中的 `call_llm()` 和 `ml_client.llm_client` 的日志，确认 `AI_PROVIDER` 与 `AI_BASE_URL` 匹配。
- `docs/upgrade-plan-v6/` 中的升级记录（Phase 0~4）也包含更早的 DeepSeek 加固笔记，可作为参考但不作为正式指南。
