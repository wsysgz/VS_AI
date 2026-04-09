# VS_AI Repository Guide

## Workspace And Remote

- Primary local workspace: `D:\GitHub\auto`
- Temporary feature work can use `D:\GitHub\worktrees\auto\<branch-name>`, but merge back into `D:\GitHub\auto` before the final push.
- Canonical Git remote: `origin = git@github.com:wsysgz/VS_AI.git`
- Preferred auth path is SSH. Verify with `ssh -T git@github.com`; the expected result is successful authentication as `wsysgz`.
- The GitHub key labeled `ssh-blog` is available locally as `C:\Users\24160\.ssh\id_ed25519.pub` with fingerprint `SHA256:5PsPPHvqPDYP7X15wLGZlQakseS8wmWYYqIYisx1Ixg`.
- A convenience SSH alias is available: `ssh -T ssh-blog`.
- Do not switch the remote back to HTTPS unless the user explicitly asks for it.
- `github-vsai-codex` is only a local备用 key alias. The primary working path for this repo is still the `ssh-blog` / default GitHub key.

## Local-First Workflow

- Change code locally first, then verify locally, then push to GitHub.
- Default verification flow:
  - `python -m pytest -q`
  - `python -m auto_report.cli run-once`
  - `git status --short`
  - `git remote -v`
- GitHub CLI is installed locally at `C:\Program Files\GitHub CLI\gh.exe`.
- Preferred GitHub CLI checks:
  - `& 'C:\Program Files\GitHub CLI\gh.exe' auth status`
  - `& 'C:\Program Files\GitHub CLI\gh.exe' repo view wsysgz/VS_AI`
  - `& 'C:\Program Files\GitHub CLI\gh.exe' run list --repo wsysgz/VS_AI --limit 5`
- If the change touches delivery channels, verify message shape locally before pushing.
- Never commit real tokens, chat IDs, or screenshots containing secrets.
- A fine-grained PAT has already been imported into local `gh auth`; keep using the local credential store instead of writing PAT values into repo files.

## Automation Rules

- User-facing scheduled delivery is one daily comprehensive report at Beijing `07:00`.
- The GitHub Actions cron is `0 23 * * *` in UTC, which maps to Beijing `07:00`.
- `push` to `main` and `workflow_dispatch` are primarily for verification and archiving; they should not become noisy user-notification channels by default.
- Keep daily automated runtime under `60` minutes. The current `Collect And Report` workflow enforces `timeout-minutes: 25`.

## Channel Rules

- PushPlus `clawbot` is the WeChat short-summary channel:
  - send `txt`
  - send a short summary plus the GitHub detail link
  - expect occasional manual reactivation / conversation refresh on the WeChat side
- Telegram is the full-report channel:
  - user must start the bot once before the bot can reach the private chat
  - send the complete report as plain text chunks of at most `4096` characters each
  - append the GitHub detail link
  - keep link previews disabled

## Repo Layout

- Workflow entry: `.github/workflows/collect-report.yml`
- App orchestration: `src/auto_report/app.py`
- Delivery integrations: `src/auto_report/integrations/`
- Rendering and archives: `src/auto_report/outputs/`
- User and handoff docs: `README.md`, `docs/USER_GUIDE.md`, `docs/TECHNICAL_GUIDE.md`

## Extension Priorities

- Future additions should layer on top of the daily report instead of fragmenting it into multiple daily pushes.
- Preferred next milestones:
  - weekly report
  - monthly report
  - more data sources
  - stronger analysis
  - better layout and reading experience
