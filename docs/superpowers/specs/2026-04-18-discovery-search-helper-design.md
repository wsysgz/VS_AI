# Discovery/Search Helper Artifact Design

> Workspace: `D:\GitHub\auto`
>
> Scope: add the smallest useful MiniMax-backed helper entrypoint for source exploration using keyword lists, without touching the main daily report chain.

## Goal

Create a standalone helper flow that:

1. reads a keyword list
2. lets MiniMax-M2.7 structure the exploration output
3. writes a stable artifact for human review
4. leaves the main report pipeline untouched

This is the first real operational landing for:

- `DISCOVERY_*`
- `SEARCH_*`
- MiniMax-backed source exploration / candidate整理

## Why this shape is right

The repo already has:

- a CLI-based artifact model
- governance JSON output
- review queue output
- prompt evaluation output

The repo does **not** yet need:

- automatic source onboarding
- auto-editing source configs
- browser automation
- OpenCLI runtime integration

So the right first step is not “automate everything”.

The right first step is:

> produce a stable, reviewable artifact from keyword-driven discovery/search work

## User flow

Example:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-discovery-search --keywords config/source_discovery/keywords.txt
```

Inputs:

- keyword file, one query per line

Outputs:

- `D:\GitHub\auto\out\discovery-search\discovery-search.json`
- `D:\GitHub\auto\out\discovery-search\discovery-search.md`

## Stage ownership

This feature is intentionally helper-stage owned.

- `discovery` -> MiniMax-M2.7
- `search` -> MiniMax-M2.7

No report-writing stage should depend on this artifact in the first batch.

## Artifact design

### JSON artifact

Top-level shape:

```json
{
  "generated_at": "...",
  "provider": "minimax_svips",
  "model": "MiniMax-M2.7",
  "keywords_path": "config/source_discovery/keywords.txt",
  "keyword_count": 3,
  "items": [
    {
      "keyword": "Anthropic news",
      "summary": "...",
      "candidates": [
        {
          "title": "...",
          "url": "...",
          "classification": "official-site",
          "confidence": "high",
          "feed_candidate": "",
          "rsshub_candidate": "",
          "changedetection_candidate": "https://...",
          "next_action": "..."
        }
      ]
    }
  ]
}
```

### Markdown artifact

Purpose:

- fast human review
- easier diffing in git / terminal

For each keyword:

- one short summary line
- a table of candidates

## Discovery strategy

The first batch should not pretend to do web-scale search.

Instead it should use a constrained, deterministic helper pattern:

1. take the keyword string
2. ask MiniMax to generate a structured candidate set
3. ask it to classify each candidate into:
   - `official-site`
   - `official-feed`
   - `rsshub-candidate`
   - `changedetection-candidate`
   - `ignore`
4. write those results as artifact only

This means the first batch is “AI-assisted exploration memo”, not autonomous source discovery.

## Input file design

Create:

- `D:\GitHub\auto\config\source_discovery\keywords.txt`

Rules:

- one keyword or source query per line
- empty lines ignored
- `#` comment lines ignored

Example:

```text
# ai-llm-agent
Anthropic news
OpenAI safety updates

# ai-x-electronics
Jetson edge AI
STM32 AI blog
Qualcomm on-device AI
```

## Code boundaries

### CLI

Add one new command:

- `build-discovery-search`

Argument:

- `--keywords <path>`

### App entrypoint

Add one small app-layer command:

- `cmd_build_discovery_search(root_dir: Path, keywords_path: str) -> Path`

### New module

Add a focused helper module for this artifact only.

Recommended:

- `D:\GitHub\auto\src\auto_report\pipeline\discovery_search.py`

Responsibilities:

- read keyword file
- build prompt
- call `call_llm(..., stage="search")` or `stage="discovery"`
- parse structured JSON response
- normalize artifact payload

### Output module

Optional split if needed, but prefer keeping first batch small.

If the pipeline module stays readable, it may directly write the artifact.

## Prompt design

Prompt should force a compact structured output.

Each candidate should include:

- `title`
- `url`
- `classification`
- `confidence`
- `feed_candidate`
- `rsshub_candidate`
- `changedetection_candidate`
- `next_action`

Prompt should also instruct the model:

- prefer official sources over aggregators
- avoid speculative claims
- mark low-confidence items clearly
- do not invent feed URLs unless labeled as candidate only

## Non-goals

This batch does not:

- verify candidates over the network
- edit `config/sources/*.yaml`
- merge results into `source_governance`
- invoke OpenCLI
- add browser-based search

## OpenCLI note

OpenCLI remains future work.

When OpenCLI pilot starts, it should be used only after external research:

- official docs
- official repo
- issues/discussions
- session/login stability
- deterministic rerun behavior

That note is important because discovery/search is exactly the kind of work that can look easy but become flaky fast.

## Verification strategy

Minimum verification:

1. CLI parser test for `build-discovery-search`
2. unit test for keyword file parsing
3. unit test for JSON response normalization
4. unit test for artifact write path
5. full `python -m pytest tests -q`

## Success criteria

This batch is successful when:

1. a keyword list can produce a JSON artifact
2. the same run also produces a Markdown review artifact
3. routing uses helper-stage ownership (`search` / `discovery`)
4. no main report code path depends on this artifact
5. the output is useful enough that you can manually review candidates without opening raw logs
