# VS_AI Morning Report Orchestration Design

Date: 2026-04-09
Topic: `VS_AI` daily single-report orchestration, push discipline, and ClawBot-first delivery
Status: Approved in conversation, written for user review

## 1. Goal

Adjust `VS_AI` so that the stable daily automation model becomes:

- one official automatic report per day
- scheduled for Beijing time `07:00`
- delivered as one combined summary report
- developed locally first, then pushed to GitHub for automatic validation and archiving
- ready for future expansion into weekly reports, monthly reports, more sources, stronger analysis, and layout improvements

This change is meant to reduce noise, control runtime budget, and make future handoff easier for both humans and AI agents.

## 2. Approved Product Decisions

The following decisions are approved for this iteration:

1. Only one daily automatic push is needed for now.
2. The daily push is the combined summary report only.
3. The daily schedule is Beijing time `07:00`.
4. Local development remains the first execution path.
5. Pushing to `main` should still trigger GitHub Actions, but that trigger is for validation and repository archiving, not for sending the official daily push to WeChat.
6. PushPlus should try `ClawBot` first because the user has already activated ClawBot listening.
7. The repository and technical docs should explicitly state that the main managed repo is `https://github.com/wsysgz/VS_AI` and the main local workspace is `D:\GitHub\auto`.

## 3. Non-Goals For This Iteration

This iteration does not implement:

- weekly report generation
- monthly report generation
- source expansion beyond what already exists
- major prompt redesign
- major renderer or layout redesign
- blog synchronization

Those remain the next planned expansion areas and should be documented as follow-up work, not mixed into this change.

## 4. Scheduling Design

### 4.1 Daily Official Run

The primary GitHub Actions workflow should keep a `schedule` trigger, but change it to:

- Beijing time: `07:00`
- UTC cron: `0 23 * * *`

This becomes the only official automatic push run for the daily report.

### 4.2 Push-To-Main Validation Run

The existing `push` trigger on `main` should remain enabled because it is valuable for ongoing development. It should:

- run the same collection and rendering pipeline
- archive outputs to `data/`
- upload artifacts
- avoid sending the user-facing WeChat push by default

This keeps development feedback fast without spamming the user during active iteration.

### 4.3 Manual Run

`workflow_dispatch` should remain available for operator use.

Manual runs should still be able to send a push when explicitly desired, but the default behavior should be conservative and align with the workflow intent.

## 5. Runtime Budget Design

The user requirement is that automatic daily runtime should not exceed `60` minutes.

To keep the system comfortably within that budget:

- scheduled automatic execution will be reduced to one daily run
- the main workflow job timeout should be capped explicitly, recommended at `25` minutes
- push-triggered validation runs will remain available but are not counted as the official daily push path

The practical intent is that the scheduled daily automation stays well below `60` minutes even as the report grows moderately. If future weekly or monthly workflows are added, they must declare and document their own runtime budgets separately.

## 6. Push Design

### 6.1 Single Combined Push

`run-once` currently generates:

- `latest-summary.md`
- `latest-ai-llm-agent.md`
- `latest-ai-x-electronics.md`

Only `latest-summary.md` should be sent automatically in this iteration.

The domain brief files remain generated and archived for later reuse, but they are not sent as separate daily messages.

### 6.2 ClawBot-First PushPlus Delivery

The PushPlus integration should be extended to support explicit channel selection.

Required behavior:

- default channel for this project becomes `clawbot`
- the integration must be able to send `channel: clawbot` to PushPlus
- if explicit ClawBot delivery fails at the API layer, the system should log the failure clearly
- a configurable fallback channel may be supported, but must not silently hide delivery problems

The first local verification should include a real test message to confirm that the active token can reach the user through ClawBot.

### 6.3 Push Discipline

Push behavior should depend on trigger intent:

- scheduled run: push enabled
- local explicit verification run: push enabled when requested
- `main` push-triggered workflow validation run: push disabled by default

This avoids accidental interruption during future development.

## 7. Configuration Design

Configuration should remain explicit and handoff-friendly.

The following additions or clarifications are recommended:

- `config/schedules.yaml`
  - record the official daily cron as `07:00 Asia/Shanghai`
- environment-driven push policy
  - `AUTO_PUSH_ENABLED`
  - `PUSHPLUS_CHANNEL`
  - optional `PUSHPLUS_FALLBACK_CHANNEL`
- documentation of trigger-specific environment policy in workflow YAML

The implementation should prefer small, explicit flags over hidden branching.

## 8. Application Flow Changes

The current application already supports:

- collecting source items
- building a combined summary
- rendering Markdown and JSON outputs
- pushing the summary through PushPlus

This iteration should refine orchestration rather than rewrite the pipeline.

Recommended flow:

1. load settings and runtime env
2. collect and analyze items
3. write summary and domain files
4. decide whether push is enabled for the current invocation
5. if push is enabled, send only the combined summary
6. write `run-status.json` with push outcome details

Push control should be externalized so local runs and workflow runs can reuse the same core code with different delivery policy.

## 9. Documentation And Handoff Requirements

The following docs must be updated so a future AI agent can resume quickly after memory reset:

- `README.md`
  - identify `VS_AI` as the main repo
  - state that the project currently sends one daily summary around `07:00` Beijing time
- `docs/USER_GUIDE.md`
  - explain the local-first workflow
  - explain that scheduled runs push once per day
  - explain that `push` to `main` is mainly for validation and archive refresh
- `docs/TECHNICAL_GUIDE.md`
  - document trigger-specific push policy
  - document ClawBot-first PushPlus behavior
  - document future roadmap: weekly report, monthly report, more sources, stronger analysis, layout optimization

These documents are part of the feature, not optional cleanup.

## 10. Testing And Verification Requirements

This change must be verified in the following order:

1. local unit tests for PushPlus payload building and orchestration behavior
2. local `run-once` execution without breaking report generation
3. local real PushPlus test targeting ClawBot
4. workflow YAML validation by running the existing test suite and checking the edited workflow file
5. push the local changes to `main` and confirm that the repository automation runs without sending an unwanted duplicate daily message

The implementation must not claim success unless the real ClawBot push attempt has been tried and its result recorded.

## 11. Risks And Tradeoffs

- ClawBot support is relatively new in PushPlus and may behave differently from the default WeChat channel.
- Keeping `push` triggers active improves developer feedback but requires careful push gating to avoid message spam.
- A single combined summary is simpler and quieter, but it means some domain detail stays inside archived files rather than daily chat messages.

These tradeoffs are acceptable for the current phase because the user explicitly prefers one daily summary and future extensibility over multiple daily pushes.

## 12. Completion Criteria

This iteration is complete when:

- the main workflow schedule is `07:00` Beijing time
- only one official daily push is sent automatically
- push-triggered workflow runs no longer send user-facing WeChat pushes by default
- local code can send a real PushPlus ClawBot test message with the configured token
- local code can still generate all report files
- `README.md`, `docs/USER_GUIDE.md`, and `docs/TECHNICAL_GUIDE.md` reflect the new operating model

## 13. Recommendation Summary

Keep `VS_AI` centered on a quiet, reliable morning workflow:

- one combined daily report
- one official scheduled push at `07:00` Beijing time
- local-first development
- GitHub `push` trigger for verification and archiving
- ClawBot-first delivery through PushPlus
- explicit documentation so future AI agents can take over quickly

This gives the project a stable operating baseline while preserving clean paths for weekly reports, monthly reports, richer sources, stronger analysis, and later layout work.
