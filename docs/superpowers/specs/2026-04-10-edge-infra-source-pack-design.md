# VS_AI Edge And Infra Source Pack Design

> Latest handoff: `docs/superpowers/status/2026-04-10-stage2-handoff.md`
>
> Status update on 2026-04-10: original parts `1 / 2 / 3` are already implemented. This design covers the next implementation slice for original part `4`.

Date: 2026-04-10
Topic: `VS_AI` second-round source expansion for high-value `AI × 电子信息 / 边缘 / 基础设施` signals
Status: Approved in conversation, written for planning

## 1. Goal

Improve the current source mix by adding a small, high-value official source pack for `AI × 电子信息 / 边缘 / 基础设施`, so the report stops being heavily skewed toward `AI / LLM / Agent`.

This slice should:

- keep the current `稳准少而精` direction
- prefer official engineering-facing sources over generic media sites
- bias toward sources that help deployment, inference, edge AI, and platform decisions
- still retain some strategic signal when it overlaps with practical engineering value

## 2. Approved Scope Decisions

The following decisions are approved for this slice:

1. Both engineering value and platform signal matter, but engineering usefulness comes first.
2. The source pack should stay small and curated rather than broad.
3. Existing `Arm` and `Qualcomm` sources stay in place.
4. The first source expansion batch should add:
   - `NVIDIA Embedded / Jetson`
   - `Google AI Edge / LiteRT`
   - `OpenVINO Blog`
   - `NXP Smarter World Blog`
5. The slice should focus on source configuration and filtering quality, not on redesigning the AI pipeline.

## 3. Problem Statement

The latest report state shows a clear imbalance:

- `ai-llm-agent`: 44 topics
- `ai-x-electronics`: 3 topics

This means later AI summarization and forecasting are operating on a skewed input mix. Before making the reasoning layer smarter, the source layer needs a stronger `AI × 电子信息 / 边缘 / 基础设施` base.

## 4. Non-Goals

This slice does not:

- expand every possible semiconductor or AI hardware source
- add generic tech media, newsletter, or marketing sites
- redesign ranking or summarization logic
- change message rendering again
- implement HTML pages or image cards

## 5. Chosen Source Pack

### 5.1 NVIDIA Embedded / Jetson

Use NVIDIA official embedded and Jetson-focused engineering posts.

Desired signal types:

- Jetson platform updates
- JetPack updates
- TensorRT / TensorRT-LLM / edge inference deployment
- robotics and embedded deployment cases

Should avoid:

- datacenter-only posts
- broad corporate announcements unrelated to edge or embedded deployment

### 5.2 Google AI Edge / LiteRT

Use official Google developer posts for on-device runtime and edge AI deployment.

Desired signal types:

- LiteRT
- AI Edge
- on-device GenAI
- NPU / GPU deployment pathways on client devices

Should avoid:

- generic Android or Chrome announcements without edge AI deployment value

### 5.3 OpenVINO Blog

Use the official OpenVINO technical blog.

Desired signal types:

- deployment optimization
- inference acceleration
- AI PC / NPU / edge runtime
- model serving or optimization workflows

Should avoid:

- broad event promotions
- ecosystem marketing without technical delivery value

### 5.4 NXP Smarter World Blog

Use NXP’s official engineering-facing blog only when entries are clearly tied to edge AI, GenAI flow, NPU, or embedded AI deployment.

Desired signal types:

- eIQ / GenAI Flow
- i.MX platform AI posts
- industrial or embedded edge AI workflows

Should avoid:

- broad corporate branding
- automotive or business posts without actionable engineering relevance

## 6. Filtering Rules

The source pack should stay useful by rejecting low-value page types before they reach later stages.

### 6.1 Title-Level Noise To Drop

Add or strengthen rejection for titles containing signals such as:

- `webinar`
- `register`
- `event`
- `ebook`
- `white paper`
- `press release`
- `partner`
- `sponsor`

These are not always useless in absolute terms, but they are too often low-value for the current morning-brief workflow.

### 6.2 URL-Level Constraints

Each new source should define explicit:

- `link_selector`
- `include_url_patterns`
- `exclude_url_patterns`

When useful, sources should also define:

- `include_title_patterns`
- `exclude_title_patterns`

The goal is to keep only pages that are likely to contain deployment, runtime, embedded, or edge-specific signal.

## 7. File Responsibilities

- `config/sources/websites.yaml`
  - add the first curated edge / infra source pack
  - encode source-specific selector and filter rules

- `src/auto_report/pipeline/source_filters.py`
  - strengthen generic title-level noise filtering when needed

- `tests/test_sources.py`
  - prove useful engineering posts survive
  - prove webinar, event, navigation, and low-value marketing titles are filtered out

## 8. Verification Requirements

This slice should be verified in the following order:

1. `python -m pytest tests/test_sources.py -v`
2. `python -m pytest -q`
3. `$env:AUTO_PUSH_ENABLED='false'; python -m auto_report.cli run-once`
4. inspect:
   - `data/reports/latest-summary.json`
   - `data/state/run-status.json`

Success means:

- `ai-x-electronics` topic presence improves meaningfully from the current low baseline
- the newly introduced items are genuinely edge / infra / deployment oriented
- obvious event, webinar, or marketing noise does not become top signal

## 9. Recommendation Summary

The right next step is not to broaden the source net.

It is to add a compact, official, engineering-useful edge and infrastructure source pack so the current pipeline receives better `AI × 电子信息` inputs before further AI-layer upgrades.
