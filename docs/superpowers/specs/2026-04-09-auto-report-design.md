# Auto Report Framework Design

Date: 2026-04-09
Topic: `auto` intelligent scheduled collection and reporting framework
Status: Draft for user review

## 1. Goal

Build a new project under `D:\GitHub\auto` that can:

- run locally and on GitHub Actions with the same CLI entry
- collect scheduled information from domestic and international sources
- focus first on two domains:
  - AI / LLM / Agent
  - electronics and information technology, especially AI-cross domains
- generate a general report plus domain briefings
- push summaries to the user
- archive outputs both locally and in GitHub
- reserve a clean interface for future blog synchronization

The first version optimizes for reliability, handoff clarity, and deployment simplicity rather than maximum source coverage.

## 2. Non-Goals For V1

The first version will not include:

- high-frequency minute-level scheduling
- heavy browser crawling as a primary collection path
- n8n or Dify as part of the main execution chain
- fully automated financial or trading recommendations
- a production web dashboard
- mandatory blog publishing in the main path

## 3. Recommended Architecture

The project will use a modular Python architecture with GitHub Actions as the default cloud scheduler.

Recommended path:

- local mode for validation and debugging
- GitHub Actions for scheduled cloud execution
- PushPlus as the first notification channel
- DeepSeek as the default LLM provider once configured
- local disk plus repository commits for report archiving

This is preferred over Cloudflare Workers as the primary runtime because the first version needs more flexible execution time, simpler debugging, and easier file-based archiving.

## 4. Runtime Modes

### 4.1 Local Mode

Local mode is used for:

- initial setup
- source debugging
- prompt and scoring validation
- manual reruns
- backfill and troubleshooting

Outputs are written into the local `data/` directory.

### 4.2 GitHub Mode

GitHub Actions runs the same CLI commands as local mode.

Each scheduled run will:

1. install dependencies
2. load configuration and secrets
3. collect and analyze data
4. generate reports
5. send push notifications
6. upload artifacts
7. commit report and state archives back to the repository

## 5. Project Structure

```text
auto/
  .github/
    workflows/
      collect-report.yml
      backfill-report.yml
  config/
    schedules.yaml
    providers.yaml
    domains/
      ai-llm-agent.yaml
      ai-x-electronics.yaml
    sources/
      rss.yaml
      github.yaml
      websites.yaml
  data/
    archives/
    reports/
    state/
    logs/
  docs/
    ARCHITECTURE.md
    TECHNICAL_GUIDE.md
    USER_GUIDE.md
    DEEPSEEK_SETUP.md
    superpowers/
      specs/
        2026-04-09-auto-report-design.md
  scripts/
    bootstrap.ps1
    bootstrap.sh
  src/
    auto_report/
      app.py
      cli.py
      settings.py
      models/
      sources/
      pipeline/
      domains/
      outputs/
      integrations/
      utils/
  tests/
  .env.example
  requirements.txt
  README.md
```

## 6. Module Responsibilities

### 6.1 `sources/`

Responsible for collection adapters.

V1 source classes:

- RSS feeds
- GitHub API
- stable public listing pages or summary pages
- small numbers of well-behaved public endpoints

Each adapter normalizes source items into a shared internal record.

### 6.2 `pipeline/`

Responsible for:

- normalization
- deduplication
- clustering similar items into topic groups
- scoring
- domain classification
- LLM analysis orchestration
- report assembly

### 6.3 `domains/`

Responsible for domain-specific rules:

- keywords
- exclusions
- topic weighting
- report templates
- label mapping

V1 domains:

- `ai_llm_agent`
- `ai_x_electronics`

### 6.4 `outputs/`

Responsible for:

- Markdown report generation
- JSON report generation
- push payload generation
- archive file writing

### 6.5 `integrations/`

Responsible for:

- PushPlus integration
- GitHub archive commit helpers
- future blog synchronization interface
- future additional push channels

## 7. Data Flow

The main execution flow for each run:

1. collect raw items from enabled sources
2. normalize all items into a shared schema
3. deduplicate by normalized URL, title fingerprint, and content hash
4. merge repeated references into topic groups with multiple evidence links
5. classify into one or more domains with one primary domain
6. run rule-based scoring and filtering
7. send shortlisted topic groups to the LLM
8. generate:
   - general summary report
   - AI / LLM / Agent briefing
   - AI x electronics briefing
9. push notification summary
10. archive reports and state locally
11. archive reports and state in GitHub during Actions runs

## 8. Output Design

### 8.1 Required Files

Each run should update at least:

- `data/reports/latest-summary.md`
- `data/reports/latest-ai-llm-agent.md`
- `data/reports/latest-ai-x-electronics.md`
- `data/reports/latest-summary.json`
- `data/state/dedup-index.json`
- `data/state/run-status.json`

Historical versions are stored under dated folders in `data/archives/`.

### 8.2 Markdown Report Structure

Recommended structure:

1. title and generated time
2. top 3 to 5 key items
3. domain highlights
4. cross-source consensus signals
5. short-term trend interpretation
6. risk and uncertainty notes
7. source link index

### 8.3 JSON Report Structure

Recommended top-level sections:

- `meta`
- `highlights`
- `signals`
- `predictions`
- `risks`
- `sources`

Markdown is optimized for human reading and blog reuse. JSON is optimized for later AI continuation, automation, and future dashboards.

## 9. Configuration Strategy

### 9.1 Environment Variables

Used for secrets and runtime-sensitive settings.

Expected examples:

- `DEEPSEEK_API_KEY`
- `GITHUB_TOKEN`
- `PUSHPLUS_TOKEN`
- `AI_BASE_URL`
- `AI_MODEL`

### 9.2 `providers.yaml`

Used for:

- primary and fallback model provider strategy
- push channel defaults
- archive behavior
- feature flags for optional integrations

### 9.3 `domains/*.yaml`

Used for:

- domain keywords
- exclusions
- weighting hints
- section titles
- template preferences

### 9.4 `sources/*.yaml`

Used for:

- source URLs
- source type
- enabled or disabled state
- fetch limit
- priority
- optional domain mapping hints

## 10. GitHub Actions Design

### 10.1 `collect-report.yml`

Primary scheduled workflow.

Responsibilities:

- checkout repository
- set up Python
- restore cache
- install dependencies
- run the main CLI command
- upload artifacts
- commit updated report and state files

Recommended actions to use:

- `actions/checkout`
- `actions/setup-python`
- `actions/cache`
- `actions/upload-artifact`
- `peter-evans/create-pull-request` or a simple repository commit flow

### 10.2 `backfill-report.yml`

Manual workflow for reruns and historical regeneration.

Expected inputs:

- date or date range
- target domain or all domains
- whether to skip push notifications

### 10.3 Scheduling Strategy

For V1:

- avoid top-of-hour scheduling
- run 2 to 4 times per day
- process recent time windows only
- archive outputs on every successful run

## 11. User Documentation Requirements

### 11.1 `TECHNICAL_GUIDE.md`

Audience:

- future AI assistants
- developers continuing the project

Must explain:

- architecture
- module boundaries
- how to add a source
- how to add a domain
- how to switch providers
- common failure paths

### 11.2 `USER_GUIDE.md`

Audience:

- end users deploying on GitHub

Must explain step by step:

1. create repository
2. prepare DeepSeek API key
3. prepare PushPlus token
4. run locally once
5. configure GitHub secrets
6. enable Actions
7. manually trigger the workflow
8. verify push, archive, and report outputs

### 11.3 `DEEPSEEK_SETUP.md`

Must explain:

- where to get a DeepSeek API key
- required environment variables
- local `.env` setup
- GitHub Secrets setup
- recommended default model
- how to validate the key

## 12. Error Handling

Errors are grouped into four classes.

### 12.1 Collection Errors

- source timeout
- rate limit
- changed page structure

Handling:

- isolate failures per source
- continue partial runs
- log missing sources
- optionally push failure notice for severe problems

### 12.2 Analysis Errors

- provider timeout
- invalid API key
- malformed model response

Handling:

- retry
- degrade to rule-based summary if needed
- mark report sections that skipped AI enhancement

### 12.3 Output Errors

- Markdown rendering issue
- archive write failure

Handling:

- always attempt to write a minimal state JSON
- never allow a successful analysis to end with zero persistent output

### 12.4 Push Errors

- notification API failure

Handling:

- do not block archiving
- store error in logs
- show failure in workflow summary

## 13. Test Strategy

Minimum V1 coverage:

- configuration loading tests
- deduplication tests
- domain classification tests
- report rendering tests
- CLI smoke tests
- workflow execution validation

## 14. Extension Interfaces

### 14.1 Blog Sync

Define a stable publish interface in `integrations/` but do not require it in the main V1 path.

### 14.2 Provider Adapter

LLM integration must use a provider abstraction so DeepSeek is the default, not a hard-coded singleton implementation.

### 14.3 Push Adapter

PushPlus is the first channel, but the push layer should allow future Server酱, WxPusher, email, or webhook channels.

### 14.4 Domain Expansion

New fields should be added by extending domain configs and domain rules first, with minimal core pipeline changes.

## 15. Implementation Sequence

Recommended sequence:

1. scaffold project structure
2. implement configuration loading and CLI
3. implement source adapters and normalization
4. implement deduplication and classification
5. implement report rendering
6. implement PushPlus
7. implement local archiving
8. implement GitHub Actions workflows
9. implement GitHub archive commit flow
10. integrate DeepSeek analysis
11. add blog sync interface stub
12. finalize technical and user docs

## 16. Completion Criteria For V1

V1 is considered complete when:

- one local command can run the full flow
- GitHub Actions can run on schedule
- three report files are generated each run
- at least one push channel works
- both local and GitHub archives are updated
- technical and user documentation are enough for handoff

## 17. Risks And Tradeoffs

- too many unstable sources in V1 will reduce reliability
- overuse of LLM analysis will increase cost and latency
- repository-based archiving is simple but can grow large over time
- prediction language must remain probabilistic and evidence-based

## 18. Recommendation Summary

Build `auto` as a Python modular reporting framework with:

- local-first validation
- GitHub Actions as the default cloud scheduler
- two initial domain packages
- Markdown and JSON outputs
- PushPlus notifications
- local and GitHub archival
- a reserved blog sync interface

This provides the fastest route to a working first version while preserving clean extension paths for future AI collaboration and additional domains.
