# VS_AI Repository Guide

## Workspace And Remote

- Primary local workspace: `D:\GitHub\auto`
- Canonical remote: `git@github.com:wsysgz/VS_AI.git`
- Prefer SSH authentication
- Final release decisions should be based on this workspace

## Project Status

- Current baseline: `364 passed`
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
- V1 closeout is complete; the next roadmap is `V2升级方案.md`

## Doc Entry Points

1. `README.md`
2. `工程手册.md`
3. `交接备忘录.md`
4. `V2升级方案.md`

## Local-First Verification

Run from `D:\GitHub\auto`:

```powershell
$env:PYTHONPATH = "src"
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
python -m auto_report.cli evaluate-prompts --dataset config/prompt_eval/baseline-v1.json
$env:AI_DISABLE_LLM = "true"
$env:AUTO_PUSH_ENABLED = "false"
python -m auto_report.cli run-once --publication-mode reviewed
python -m auto_report.cli build-pages
python -m auto_report.cli build-ops-dashboard
python -m auto_report.cli build-source-governance
python -m auto_report.cli build-review-queue
```

### Codex Local Review Policy

- Local validation is executed and reviewed by Codex in this workspace.
- Do not call DeepSeek solely to validate local code changes.
- Set `$env:AI_DISABLE_LLM='true'` for deterministic local acceptance runs.
- Compare AI-generated artifacts against repo truth, tests, and rendered outputs before trusting them.

### Remote Run Policy

- Default to local-first verification.
- Do not run GitHub Actions for every intermediate change.
- Push before any `workflow_dispatch`; the remote workflow runs pushed code only.
- After a remote trigger, record run id / URL and continue local work unless the next task depends on the result.
- Treat GitHub Actions as final confirmation, not the primary debug loop.

## Phase Execution Discipline

- Prefer stage-by-stage delivery over mixed parallel polishing.
- Close code, docs, and verification for the active stage before opening the next one.
- Record later ideas in `V2升级方案.md` instead of mixing them into the current batch.

## AI Provider Notes

- OpenAI-compatible providers are supported through `src/auto_report/integrations/llm_client.py`.
- Confirmed providers:
  - DeepSeek official: `AI_PROVIDER=deepseek`, `AI_BASE_URL=https://api.deepseek.com`
  - MiniMax-M2.7 via OpenAI-compatible endpoint: `AI_PROVIDER=minimax_svips`, `AI_BASE_URL=https://api.svips.org/v1`
  - LiteLLM gateway: `AI_PROVIDER=litellm_proxy`, `AI_BASE_URL=http://127.0.0.1:4000`
- Stage-level routing is supported; keep provider policy explicit in docs and validation notes.

## Key Operational Truths

1. `data/state/run-status.json` is the source of truth for delivery, risk, AI metrics, and runtime status.
2. Feishu is the only active delivery channel.
3. Notifications always include both the public site and the GitHub raw report link.
4. `publication_mode=reviewed` writes reviewed metadata into reports, state, notifications, and Pages cards.
5. Generated local artifacts under `out/` and `output/` may be absent in a clean workspace and should be rebuilt when needed.

## Key Paths

- Workflows: `.github/workflows/`
- Source: `src/auto_report/`
- Tests: `tests/`
- Config: `config/`
- Reports: `data/reports/`
- Runtime state: `data/state/run-status.json`
- Public Pages output: `docs/`
- Historical planning leftovers kept on purpose:
  - latest plan under `docs/superpowers/plans/`
  - latest spec under `docs/superpowers/specs/`

## Common Gotchas

1. Always set `$env:PYTHONPATH='src'` before local Python commands.
2. Use `source_stats.report_topics`; do not reintroduce `filtered_topics`.
3. Public `limitations` should stay editorial; source failures belong in `source_health`.
4. Workflow output writeback is concurrency-sensitive; keep the current snapshot-and-replay push strategy in reusable workflows.
5. For blocked official sources, verify the full evidence chain before deciding whether the issue is requests-only, curl-only, or extractor-level.
