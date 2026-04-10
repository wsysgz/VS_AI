# VS_AI Precision Source And AI Pipeline Design

> Latest handoff: `docs/superpowers/status/2026-04-10-stage2-handoff.md`
>
> Status update on 2026-04-10: the first-round design and the second-round executive briefing presentation upgrade have already been implemented and verified locally. Remaining user-requested work now starts from original items `4 / 5`.

Date: 2026-04-10
Topic: `VS_AI` first local upgrade for precise source expansion, staged AI analysis/summarization/forecasting, and stronger morning brief presentation
Status: Approved in conversation, written for planning

## 1. Goal

Upgrade `VS_AI` from a first-pass report generator into a stable morning-brief system that:

- keeps the current Beijing `07:00` daily automation model
- prefers fewer but higher-value information sources instead of broad, noisy collection
- lets the called AI read repository-local pre-reading documents before analysis, summarization, and forecasting
- upgrades the pipeline from one AI summary enhancement into three explicit AI stages
- produces a sharper WeChat short brief and a more complete Telegram full brief
- still runs locally first and can later move to GitHub Actions without depending on the operator's desktop files

This iteration is about raising signal quality and reasoning quality while preserving operational stability.

## 2. Approved Product Decisions

The following decisions are approved for this iteration:

1. This first upgrade prioritizes `稳准少而精` rather than broad source expansion.
2. The three uploaded methodology documents become repository assets and runtime inputs.
3. The called AI must read repository-local copies of those documents at runtime instead of depending on `C:\Users\24160\Desktop\...`.
4. The AI flow must become staged: analysis first, summarization second, forecasting third.
5. The daily official automation time remains Beijing `07:00`.
6. WeChat remains the short morning summary channel.
7. Telegram remains the full-text complete brief channel.
8. This iteration is local-first: verify locally before pushing to the repository automation.

## 3. External Reference Cases

The design direction is informed by the following cases and papers:

1. Anthropic Economic Index, which first structures raw interactions before producing higher-level findings.
2. Anthropic Economic Primitives, which standardizes analysis questions before aggregation.
3. `Large Language Model Enhanced Clustering for News Event Detection`, which supports using LLM-assisted topic/event grouping before summarization.
4. `From News to Forecast`, which separates news filtering, reasoning, and forecasting instead of treating prediction as a single prompt.
5. `MIRAI`, which treats forecasting as a multi-step process with explicit evidence use and scenario handling.
6. OpenAI business application case studies such as Hex, HubSpot, and LSEG, which use structured data analysis before executive-style brief generation.

These references support the core decision to move from one-shot summarization to a staged reasoning pipeline with explicit structure and explicit fallbacks.

## 4. Non-Goals For This Iteration

This iteration does not implement:

- broad source coverage across every possible AI and electronics publication
- image cards, HTML newsletters, or browser-rendered message layouts
- weekly or monthly report generation
- blog synchronization
- historical backfill redesign
- multi-model orchestration beyond the current DeepSeek-compatible provider path

Those remain later expansion areas once this new baseline is stable.

## 5. Source Strategy

### 5.1 Principle

Sources should become `official + valuable + stable + recent`.

The current system has two major weaknesses:

1. generic website scraping collects navigation noise such as `Home`, `Subscribe`, and document anchor links
2. generic GitHub repository search overweights popularity and underweights editorial relevance

This iteration should replace breadth-first collection with selective collection and stronger filtering.

### 5.2 Source Tiers

The source set should be reorganized into three tiers:

#### Tier 1: Official AI release and research sources

Primary examples:

- OpenAI News RSS
- Hugging Face Blog RSS
- Anthropic news or research listing pages
- DeepSeek update or news pages instead of the generic docs homepage
- Qwen official blog
- Moonshot / Kimi platform blog

These sources carry the highest product and model-release signal.

#### Tier 2: Official edge AI and hardware sources

Primary examples:

- Arm newsroom items relevant to edge AI, NPU, on-device inference, and ExecuTorch
- Qualcomm OnQ and release posts relevant to robotics, edge AI, or intelligent edge
- NVIDIA technical blog items relevant to Jetson, robotics, or edge deployment

These sources anchor the `AI × 电子信息` domain with higher-quality signals than generic semiconductor index pages.

#### Tier 3: Curated GitHub watchlist

GitHub should shift from generic repository search to a curated watchlist of repositories whose updates are genuinely meaningful for the target domains.

Representative examples:

- `langchain-ai/langgraph`
- `vllm-project/vllm`
- `ollama/ollama`
- `pytorch/executorch`
- `alibaba/MNN`
- `tenstorrent/tt-metal`

GitHub becomes a product/toolchain signal source, not the main discovery engine.

### 5.3 Filtering Rules

This iteration should add explicit filtering rules before items ever reach analysis:

- drop titles that match generic navigation or site furniture words such as `Home`, `Subscribe`, `Pricing`, `Docs`, `Jobs`, `About`
- drop URLs that point to category pages, tag pages, anchor-only links, pricing pages, or jobs/about pages
- require minimum title length and useful path patterns
- prefer recent items within a controlled window
- cap item counts per source aggressively
- deduplicate repeated links before later topic grouping

The intent is that AI should analyze fewer, cleaner items instead of spending tokens on site scaffolding.

## 6. Repository-Local AI Reading Assets

### 6.1 File Placement

The three uploaded methodology files should be copied into the repository under:

- `config/ai_reading/analysis-before.md`
- `config/ai_reading/summary-before.md`
- `config/ai_reading/forecast-before.md`

These files become part of the deployable application, not operator-local dependencies.

### 6.2 Runtime Access Model

The called AI should not be expected to reach into arbitrary local desktop paths.

Instead, the application should:

1. read the repository-local Markdown file for the current stage
2. combine that content with the current structured topic/report payload
3. send both as the AI request content

This guarantees the same behavior locally and on GitHub Actions while the desktop machine is offline or shut down.

### 6.3 Prompt Loader

Add a small prompt-loading layer responsible for:

- locating the three repository files
- reading them as UTF-8 text
- surfacing clear errors if a required file is missing
- exposing stage-specific pre-reading text to the AI pipeline

This should remain separate from the DeepSeek HTTP adapter so prompt management and transport logic stay decoupled.

## 7. Pipeline Design

### 7.1 Current Flow

Current simplified flow:

`collect -> deduplicate -> score -> render -> optional one-shot AI enhancement -> push`

### 7.2 Target Flow

New flow for this iteration:

`curated collect -> source filtering -> topic grouping -> analysis stage -> summarization stage -> forecasting stage -> channel rendering -> archive -> optional push`

### 7.3 Topic Grouping

Before AI is called, raw items should be grouped into topic candidates with richer context than the current URL-only grouping.

Each topic candidate should carry at least:

- canonical title
- canonical URL
- primary domain candidate
- matched domains
- evidence count
- source IDs
- condensed evidence snippets
- merged tags

The goal is to give the AI a stable, compact unit of meaning per topic.

## 8. Staged AI Design

### 8.1 Analysis Stage

Input:

- one topic candidate
- repository text from `analysis-before.md`

Output:

- structured analysis object, not free-form prose

Recommended fields:

- `situation`
- `facts`
- `contradictions`
- `primary_contradiction`
- `sides_analysis`
- `self_deception_risk`
- `core_insight`
- `confidence`

This stage converts topic information into reusable analytical building blocks.

### 8.2 Summarization Stage

Input:

- the collection of topic analyses
- repository text from `summary-before.md`

Output:

- one structured combined brief payload
- one structured payload per supported domain

Recommended fields:

- `one_line_core`
- `executive_summary`
- `key_points`
- `key_insights`
- `limitations`
- `actions`

This stage converts many topic analyses into reader-facing report structure.

### 8.3 Forecasting Stage

Input:

- topic analyses
- summary payload
- recent topic distribution metadata
- repository text from `forecast-before.md`

Output:

- structured forecast payload

Recommended fields:

- `candidate_routes`
- `best_case`
- `worst_case`
- `most_likely_case`
- `chain_reactions`
- `key_variables`
- `forecast_conclusion`
- `confidence`

This stage should remain cautious and scenario-based rather than pretending certainty.

## 9. Fallback And Reliability Design

The `07:00` automation requirement is more important than perfect AI output on any single run.

Therefore each AI stage must be independently recoverable:

- if per-topic analysis fails, that topic falls back to a rule-based analysis stub
- if summarization fails, the combined and domain briefs fall back to deterministic renderer content
- if forecasting fails, the report should explicitly state that no forecast was produced this round

Fallback behavior must be explicit in both run status and report content. The system must not silently pretend a full AI path succeeded when it did not.

## 10. Rendering Design

### 10.1 WeChat Short Brief

The WeChat brief should become a structured morning digest with five compact blocks:

1. headline and timestamp
2. one-sentence main judgment
3. three key signals
4. one risk reminder
5. detail link

The writing style should be short, crisp, and useful within 30 seconds.

### 10.2 Telegram Full Brief

The Telegram brief should become a longer structured report with:

1. title and timestamp
2. one-line core judgment
3. executive summary
4. topic signal section
5. key insights section
6. short-term forecast section
7. limitations or uncertainty section
8. detail link

The output stays plain text for robustness, but should read like a publication rather than a log dump.

### 10.3 Markdown Archive

The archived Markdown report should remain the canonical long-form artifact and include:

- combined summary
- selected topic analyses
- forecast section
- fallback notes when relevant

This archive remains the source for GitHub repository viewing and Telegram full-text delivery.

## 11. Run Status And Observability

`data/state/run-status.json` should be expanded to include:

- stage success or fallback state for `analysis`, `summary`, and `forecast`
- source usage counts
- topic counts before and after filtering
- whether AI was used
- push responses per channel
- overall generated files

This makes future debugging and handoff much easier than the current pushed/not-pushed view.

## 12. File Layout Changes

The following new or changed files are expected in this iteration:

- new configuration assets under `config/ai_reading/`
- source updates in `config/sources/*.yaml`
- new prompt-loading helper under `src/auto_report/pipeline/`
- new source filtering helper under `src/auto_report/pipeline/`
- source extractor changes under `src/auto_report/sources/`
- staged AI pipeline orchestration under `src/auto_report/pipeline/`
- richer renderers under `src/auto_report/outputs/`
- expanded tests for settings, sources, pipeline, rendering, and run status

The exact implementation file split should preserve the current modular layout and avoid pushing all behavior into `app.py`.

## 13. Testing And Verification Requirements

This iteration should be verified locally in this order:

1. unit tests for prompt loading and settings integration
2. unit tests for source filtering and extractor behavior
3. unit tests for AI stage parsing and fallback behavior
4. unit tests for channel rendering
5. local `python -m pytest -q`
6. local `python -m auto_report.cli run-once`
7. inspection of:
   - `data/reports/latest-summary.md`
   - `data/reports/latest-summary.json`
   - `data/state/run-status.json`

Success means:

- obvious navigation junk no longer appears as topic signals
- the report includes visible analysis, summary, and forecast structure
- repository-local prompt assets are used
- the pipeline still finishes locally without breaking the current daily workflow model

## 14. Risks And Tradeoffs

- More structure means more code paths, so parsing and fallback logic must stay conservative.
- Some official websites may still need selector tuning; stability is better than collecting from every possible source immediately.
- Structured AI output improves reliability, but only if the parser rejects malformed output clearly.
- A smaller source set may temporarily reduce breadth, but this is acceptable because the user explicitly prefers quality over coverage in the first upgrade.

## 15. Completion Criteria

This first local upgrade is complete when:

- the three methodology Markdown files live inside the repository
- the runtime AI path reads those repository files by stage
- source collection no longer surfaces obvious webpage furniture as report topics
- the report pipeline runs through staged `analysis -> summary -> forecast` logic with explicit fallback
- WeChat short text looks like a morning digest rather than a raw list
- Telegram full text looks like a structured complete brief
- local verification passes before any repository automation rollout

## 16. Recommendation Summary

The right first upgrade is not to chase more volume.

It is to make `VS_AI` think and present information more like a disciplined analyst:

- read the right pre-analysis documents
- collect fewer, cleaner, more authoritative signals
- analyze before summarizing
- summarize before forecasting
- render differently for short-form and full-form channels
- fail safely so the `07:00` workflow remains dependable

That gives the project a much stronger base for later broad source expansion, better visuals, and stronger automated operation.
