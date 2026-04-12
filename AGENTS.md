# VS_AI Repository Guide

## Workspace And Remote

- Primary local workspace: `D:\GitHub\auto`
- Reference mirror for takeover comparison: `D:\AI\workbuddy\auto\auto`
- Temporary feature work can use `D:\GitHub\worktrees\auto\<branch-name>`, but final verification and release decisions should be based on `D:\GitHub\auto`.
- Canonical Git remote: `origin = git@github.com:wsysgz/VS_AI.git`
- Preferred auth path is SSH. Verify with `ssh -T git@github.com`; the expected result is successful authentication as `wsysgz`.
- The GitHub key labeled `ssh-blog` is available locally as `C:\Users\24160\.ssh\id_ed25519.pub` with fingerprint `SHA256:5PsPPHvqPDYP7X15wLGZlQakseS8wmWYYqIYisx1Ixg`.
- A convenience SSH alias is available: `ssh -T ssh-blog`.
- Do not switch the remote back to HTTPS unless the user explicitly asks for it.
- `github-vsai-codex` is only a local backup key alias. The primary working path for this repo is still the `ssh-blog` / default GitHub key.

## Project Status (2026-04-12)

- **V6 Phase 0~4 全部完成**, Phase 5 暂缓
- **测试**: 190 passed, 0 failed
- **CI**: reusable workflow 主链已覆盖 workflow-guard → test → collect → analyze → report → deploy-pages / ops-dashboard / review-queue
- **数据源**: RSS(6) + GitHub(4组) + Websites + Hacker News + ArXiv
- **LLM**: 统一客户端（DeepSeek / OpenAI 兼容），Analysis 5路并行
- **推送**: PushPlus(ClawBot) + Telegram + 飞书 三通道，三端正文统一携带公开站首页 + GitHub 原文双链接

## 接手入口

1. **完整接手手册**: `docs/HANDOFF.md` ← **优先读这个**
2. **快速启动**: README.md → 3 步跑起来
3. **升级与审计资料**: `docs/upgrade-plan/README.md`

## Local-First Workflow

- Change code locally first, verify locally, then push to GitHub.
- Default verification flow:
  ```powershell
  cd D:\GitHub\auto
  $env:PYTHONPATH = "src"
  pwsh ./scripts/check-workflows.ps1 -Profile full
  python -m pytest tests -q           # 预期 190 passed
  python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
  python -m auto_report.cli run-once --publication-mode reviewed   # 完整运行一次
  cat data/state/run-status.json       # 检查状态
  ```
- GitHub CLI is installed locally at `C:\Program Files\GitHub CLI\gh.exe`.
- If the change touches delivery channels, verify message shape locally before pushing.
- Never commit real tokens, chat IDs, or screenshots containing secrets.

## Automation Rules

- User-facing scheduled delivery is one daily comprehensive report at Beijing `07:00`.
- The GitHub Actions cron is `0 23 * * *` in UTC, which maps to Beijing `07:00`.
- `push` to `main` and `workflow_dispatch` are primarily for verification and archiving; they should not become noisy user-notification channels by default.
- Keep daily automated runtime under `60` minutes. Current 5-job pipeline enforces per-job timeouts (test=5min, collect=15min, analyze=35min, report=10min, pages=5min).

## Channel Rules

- PushPlus `clawbot` is the WeChat short-summary channel:
  - send `txt`
  - send a short summary plus the public site link and GitHub raw report link
  - expect occasional manual reactivation / conversation refresh on the WeChat side
- Telegram is the full-report channel:
  - user must start the bot once before the bot can reach the private chat
  - send the complete report as plain text chunks of at most `4096` characters each
  - append the public site link and GitHub raw report link
  - keep link previews disabled
- Feishu is the medium-length structured channel and also appends the public site link and GitHub raw report link.

## Repo Layout

- Workflow entry: `.github/workflows/collect-report.yml` (5 jobs)
- App orchestration: `src/auto_report/app.py` (StageTimer + run_once/render_reports)
- Pipeline core: `src/auto_report/pipeline/analysis.py` (build_report_package)
- AI pipeline: `src/auto_report/pipeline/ai_pipeline.py` (staged 3-phase AI)
- LLM client: `src/auto_report/integrations/llm_client.py` (unified DeepSeek/OpenAI)
- Data sources: `src/auto_report/sources/collector.py` (4-source parallel collection)
- Delivery integrations: `src/auto_report/integrations/`
- Rendering and archives: `src/auto_report/outputs/`
- Test suite: `tests/` (190 passing tests across 28 files)
- Handoff docs: `docs/HANDOFF.md`, `AGENTS.md`, `README.md`
- Upgrade plan: `docs/upgrade-plan/`

## Key Gotchas for Developers

1. **render_reports() 返回 tuple**: `(list[str], dict[str,float], dict[str,object])` — 调用方必须完整解包
2. **AI 不要外部重复调**：`build_report_package()` 内部已完成 AI 三阶段，不要在 app.py 再调 `run_staged_ai_pipeline()`
3. **Windows 路径坑**：`_to_relative_paths()` 已处理，新增路径处理代码记得统一正斜杠
4. **run-status source 口径**：统一使用 `source_stats.report_topics`，不要再写 `filtered_topics`
5. **reviewed 元数据**：reviewer / review_note 只在 `publication_mode=reviewed` 时写入报告、通知和 Pages 卡片
6. **data/ 不用手动提交**：CI 的 `git-auto-commit-action` 会自动归档
7. **新增数据源**：改 collector.py + config YAML + 对应 source 文件，三处联动

## Extension Priorities

- Future additions should layer on top of the daily report instead of fragmenting it into multiple daily pushes.
- Phase 5 candidates (not started): MCP Server, email subscription, bilingual reports, knowledge enrichment, weekly/monthly reports.
