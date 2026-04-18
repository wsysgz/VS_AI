# First-Batch RSSHub Candidates

> Workspace: `D:\GitHub\auto`
>
> Goal: produce a reviewable first-batch mapping for RSSHub / stable-feed replacement work without changing `config/sources/*.yaml` yet.

## Scope

This document is intentionally lighter than implementation work.

- It does **not** change source config
- It does **not** claim any route below is already verified
- It does **not** override current stable sources already landed in `rss.yaml`
- It gives the next execution pass a small, prioritized candidate list

## Selection rules

First-batch candidates are chosen from sources that are currently:

- high-value for the main report themes
- still represented as fragile listing sources in governance output
- good fits for "try official feed first, then RSSHub if needed"

Excluded from this batch:

- sources already stabilized in `D:\GitHub\auto\config\sources\rss.yaml`
- sources already moved to JSON API / structured page collection and no longer urgent
- manual-replace items that are better solved by a direct source replacement than by RSSHub

## First batch

| source_id | domain | current_url | candidate_route_or_feed | type | priority | notes |
|---|---|---|---|---|---|---|
| `anthropic-news` | `ai-llm-agent` | `https://www.anthropic.com/news` | Anthropic news/feed equivalent if available; otherwise RSSHub-style website route research | `official-feed-first` | `P1` | High-value AI source, still modeled as fragile listing in governance output |
| `arm-news` | `ai-x-electronics` | `https://newsroom.arm.com/news` | ARM newsroom/news feed or RSSHub website route research | `rsshub-or-official-feed` | `P1` | Good candidate because newsroom-style sites often have hidden feed surfaces even when listing HTML is fragile |
| `qualcomm-onq` | `ai-x-electronics` | `https://www.qualcomm.com/news/onq` | Qualcomm OnQ feed if available; otherwise RSSHub-style news route research | `rsshub-or-official-feed` | `P1` | High-value edge/SoC source and still a plain listing collector |
| `nvidia-embedded` | `ai-x-electronics` | `https://developer.nvidia.com/blog/tag/jetson/` | NVIDIA developer blog tag feed if available; otherwise RSSHub-style developer blog route research | `official-feed-first` | `P1` | Important Jetson / edge source; tag pages are structurally fragile even when currently usable |
| `infineon-blog` | `ai-x-electronics` | `https://www.infineon.com/cms/en/about-infineon/press/press-releases/` | Infineon press/news feed if available; otherwise RSSHub-style press route research | `rsshub-or-official-feed` | `P2` | Valuable but slightly lower urgency than ARM / Qualcomm / NVIDIA |

## Deferred but not first-batch

These are worth tracking, but I would not put them in the first RSSHub execution wave.

| source_id | current_state | recommendation |
|---|---|---|
| `deepseek-updates` | already moved to `structured_page` | keep current collector unless it becomes noisy again |
| `qwen-blog` | already moved to `json_api` | do not spend RSSHub effort now |
| `moonshot-blog` | already moved to `structured_page` | do not spend RSSHub effort now |
| `openvino-blog` | already moved to `structured_page` | treat as changedetection / feed research later, not first-batch |
| `google-ai-edge` | already stabilized in `rss.yaml` | no RSSHub work needed now |
| `st-blog` | already stabilized in `rss.yaml` | governance artifact should be considered stale here; no immediate RSSHub work needed |

## Manual-replace, not RSSHub-first

These items should not be mixed into the first RSSHub batch.

| source_id | why not first-batch RSSHub |
|---|---|
| `meta-ai-blog` | current issue is a direct feed replacement / verification problem, not an obvious RSSHub-first target |
| `nxp-edge-ai` | current strategy is direct replacement toward a stable GitHub / official source direction |
| `ti-e2e-blog` | already moved to JSON API in `websites.yaml`; not an RSSHub-first problem now |

## Recommended execution order

When you move from this mapping doc to actual validation work, the order should be:

1. `anthropic-news`
2. `nvidia-embedded`
3. `arm-news`
4. `qualcomm-onq`
5. `infineon-blog`

Reasoning:

- `anthropic-news` is a top-tier AI source and directly affects the core report theme
- `nvidia-embedded`, `arm-news`, and `qualcomm-onq` are the strongest edge/electronics sources still exposed as fragile listings
- `infineon-blog` is useful, but lower urgency than the three above

## Suggested next pass

The next implementation pass should not blindly add routes. It should validate each row with this checklist:

1. check whether an official feed already exists
2. if no official feed is obvious, check whether RSSHub has a route that matches the site pattern
3. record the candidate in a structured table with:
   - confirmed URL
   - source type
   - sample item count
   - last check date
   - fit for current category filters
4. only after that, change `config/sources/*.yaml`

## Working assumption

This batch assumes the project should prefer:

`official feed > stable JSON/API > RSSHub route > changedetection watch > brittle listing polling`

That keeps the rollout aligned with the repo's current P1 goal: source stability first, not collector cleverness.
