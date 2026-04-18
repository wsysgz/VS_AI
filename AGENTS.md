# VS_AI Repository Guide

## Workspace And Remote

- Primary local workspace: `D:\GitHub\auto`
- Canonical remote: `git@github.com:wsysgz/VS_AI.git`
- Prefer SSH authentication
- Final release decisions should be based on this workspace, not temporary mirrors or old worktrees

## Project Status

- Current baseline: `210 passed`
- Main workflow chain:
  - workflow guard
  - tests
  - collect
  - analyze
  - report
  - pages
  - ops dashboard
  - review queue
- Public site entry: `https://wsysgz.github.io/VS_AI/`

## Doc Entry Points

1. `README.md`
2. `AI对接手册.md`
3. `用户操作手册.md`
4. `V1升级方案.md`
5. `交接备忘录.md`

## Local-First Verification

Run from `D:\GitHub\auto`:

```powershell
$env:PYTHONPATH = "src"
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
$env:AUTO_PUSH_ENABLED = "false"
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
```

### Remote Run Policy

- Default to local-first verification for all normal development work.
- Do **not** run GitHub Actions for every intermediate change; remote runs are reserved for project-plan completion, stage completion, or explicit release-style checkpoints.
- Before any push or manual `workflow_dispatch`, confirm the local validation chain is clean enough for the scope of the change.
- Treat GitHub Actions as final confirmation, not as the primary debug loop.

## AI Provider Notes

- The current repo already supports OpenAI-compatible providers through `src/auto_report/integrations/llm_client.py`.
- Confirmed switchable providers:
  - DeepSeek official: `AI_PROVIDER=deepseek`, `AI_BASE_URL=https://api.deepseek.com`, `AI_MODEL=deepseek-chat`
  - MiniMax-M2.7 via third-party OpenAI-compatible endpoint: `AI_PROVIDER=minimax_svips`, `AI_BASE_URL=https://api.svips.org/v1`, `AI_MODEL=MiniMax-M2.7`
- Current limitation: one provider is active per run.
- Stage-level multi-model routing is a P2 item; until then, do not assume `analysis`, `summary`, and `forecast` can use different providers in the same run unless code explicitly supports it.

## Key Operational Truths

1. `data/state/run-status.json` is the source of truth for delivery, risk, AI metrics, source health, source registry, and source governance.
2. `workflow_dispatch` runs the pushed remote ref, not local unpushed changes.
3. Notifications always include both:
   - `https://wsysgz.github.io/VS_AI/`
   - the current GitHub raw report link
4. `publication_mode=reviewed` writes reviewed metadata into reports, state, notifications, and Pages cards.
5. Local workflow validation profiles are fixed to `daily`, `recovery`, and `full`.

## Key Paths

- Workflows: `.github/workflows/`
- Source: `src/auto_report/`
- Tests: `tests/`
- Config: `config/`
- Reports: `data/reports/`
- Runtime state: `data/state/run-status.json`
- Source governance artifact: `out/source-governance/source-governance.json`
- Public Pages output: `docs/`

## Common Gotchas

1. Always set `$env:PYTHONPATH='src'` before local Python commands on this machine.
2. Use `source_stats.report_topics`; do not reintroduce `filtered_topics`.
3. Public `limitations` should stay editorial; source failures belong in `source_health`.
4. Workflow output writeback is concurrency-sensitive; keep the current snapshot-and-replay push strategy in reusable workflows.

