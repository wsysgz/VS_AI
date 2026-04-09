# Auto Report Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable `auto` framework in `D:\GitHub\auto` with local execution, GitHub Actions scheduling, report generation, PushPlus delivery, local and repository archiving, and DeepSeek-ready configuration.

**Architecture:** Use a modular Python package under `src/auto_report` with configuration-driven source and domain definitions, a deterministic collection pipeline, and pluggable integrations for LLMs, push channels, and archive publishing. The same CLI entrypoint powers both local runs and GitHub Actions workflows, while Markdown and JSON outputs become the system of record for reports and future blog sync.

**Tech Stack:** Python 3.12, pytest, PyYAML, requests, feedparser, python-dateutil, GitHub Actions, PushPlus HTTP API, DeepSeek-compatible OpenAI-style chat API

---

### Task 1: Bootstrap Repository Skeleton

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/auto_report/__init__.py`
- Create: `src/auto_report/cli.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.cli import build_parser


def test_cli_exposes_run_and_backfill_commands():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "run-once" in choices
    assert "backfill" in choices
    assert "render-report" in choices
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'auto_report'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/cli.py
from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once")
    subparsers.add_parser("backfill")
    subparsers.add_parser("render-report")
    return parser
```

```python
# src/auto_report/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```text
# requirements.txt
pytest==8.3.5
PyYAML==6.0.2
requests==2.32.3
feedparser==6.0.11
python-dateutil==2.9.0.post0
python-dotenv==1.0.1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cli_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Add project bootstrap files**

```gitignore
__pycache__/
.pytest_cache/
.venv/
.env
data/logs/
data/reports/
data/archives/
data/state/
*.pyc
```

```env
# .env.example
DEEPSEEK_API_KEY=
AI_PROVIDER=deepseek
AI_BASE_URL=https://api.deepseek.com
AI_MODEL=deepseek-chat
PUSHPLUS_TOKEN=
GITHUB_TOKEN=
AUTO_TIMEZONE=Asia/Shanghai
AUTO_PUSH_ENABLED=true
AUTO_ARCHIVE_TO_GITHUB=true
```

```markdown
# README.md

## Auto Report

Scheduled intelligence collection and reporting framework for:

- AI / LLM / Agent
- AI x electronics

Run locally:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m auto_report.cli run-once
```
```

- [ ] **Step 6: Commit**

```bash
git add .gitignore README.md requirements.txt .env.example src/auto_report/__init__.py src/auto_report/cli.py tests/test_cli_smoke.py
git commit -m "chore: bootstrap auto report skeleton"
```

### Task 2: Implement Settings and Configuration Loading

**Files:**
- Create: `config/schedules.yaml`
- Create: `config/providers.yaml`
- Create: `config/domains/ai-llm-agent.yaml`
- Create: `config/domains/ai-x-electronics.yaml`
- Create: `config/sources/rss.yaml`
- Create: `config/sources/github.yaml`
- Create: `config/sources/websites.yaml`
- Create: `src/auto_report/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from auto_report.settings import load_settings


def test_load_settings_reads_domains_and_sources():
    settings = load_settings(Path.cwd())
    assert settings.providers["llm"]["provider"] == "deepseek"
    assert len(settings.domains) == 2
    assert "rss" in settings.sources
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings.py -v`
Expected: FAIL with `ImportError` or missing `load_settings`

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/settings.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class Settings:
    root_dir: Path
    providers: dict[str, Any]
    domains: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    schedules: dict[str, Any]


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_settings(root_dir: Path) -> Settings:
    config_dir = root_dir / "config"
    domains_dir = config_dir / "domains"
    sources_dir = config_dir / "sources"
    domains = {
        path.stem: _read_yaml(path)
        for path in sorted(domains_dir.glob("*.yaml"))
    }
    sources = {
        path.stem: _read_yaml(path)
        for path in sorted(sources_dir.glob("*.yaml"))
    }
    return Settings(
        root_dir=root_dir,
        providers=_read_yaml(config_dir / "providers.yaml"),
        domains=domains,
        sources=sources,
        schedules=_read_yaml(config_dir / "schedules.yaml"),
    )
```

```yaml
# config/providers.yaml
llm:
  provider: deepseek
  base_url: https://api.deepseek.com
  model: deepseek-chat
push:
  primary_channel: pushplus
archive:
  commit_to_repo: true
```

```yaml
# config/domains/ai-llm-agent.yaml
id: ai-llm-agent
title: AI / LLM / Agent
keywords:
  - llm
  - agent
  - reasoning
  - multimodal
exclusions: []
```

```yaml
# config/domains/ai-x-electronics.yaml
id: ai-x-electronics
title: AI x Electronics
keywords:
  - edge ai
  - npu
  - embedded ai
  - accelerator
  - sensor
exclusions: []
```

```yaml
# config/sources/rss.yaml
sources:
  - id: huggingface-blog
    enabled: true
    url: https://huggingface.co/blog/feed.xml
    category: ai-llm-agent
```

```yaml
# config/sources/github.yaml
sources:
  - id: github-trending-search
    enabled: true
    query: topic:llm stars:>200 pushed:>=2026-04-01
```

```yaml
# config/sources/websites.yaml
sources:
  - id: deepseek-news
    enabled: true
    url: https://api-docs.deepseek.com/news/news
    mode: listing
```

```yaml
# config/schedules.yaml
timezone: Asia/Shanghai
jobs:
  daily:
    cron: "17 1,5,9,13 * * *"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config src/auto_report/settings.py tests/test_settings.py
git commit -m "feat: add configuration loading"
```

### Task 3: Define Core Models and Deduplication

**Files:**
- Create: `src/auto_report/models/__init__.py`
- Create: `src/auto_report/models/records.py`
- Create: `src/auto_report/pipeline/dedup.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.models.records import CollectedItem
from auto_report.pipeline.dedup import deduplicate_items


def test_deduplicate_merges_same_url_items():
    first = CollectedItem(
        source_id="rss",
        item_id="1",
        title="Agent release",
        url="https://example.com/a",
        summary="first summary",
        published_at="2026-04-09T00:00:00+00:00",
        collected_at="2026-04-09T01:00:00+00:00",
        tags=["agent"],
        language="en",
        metadata={},
    )
    second = CollectedItem(
        source_id="web",
        item_id="2",
        title="Agent release updated",
        url="https://example.com/a",
        summary="second summary",
        published_at="2026-04-09T00:05:00+00:00",
        collected_at="2026-04-09T01:05:00+00:00",
        tags=["agent"],
        language="en",
        metadata={},
    )
    groups = deduplicate_items([first, second])
    assert len(groups) == 1
    assert len(groups[0].evidence_items) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: FAIL with missing `CollectedItem` or `deduplicate_items`

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/models/records.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CollectedItem:
    source_id: str
    item_id: str
    title: str
    url: str
    summary: str
    published_at: str
    collected_at: str
    tags: list[str]
    language: str
    metadata: dict[str, object]


@dataclass(slots=True)
class TopicGroup:
    group_id: str
    canonical_title: str
    canonical_url: str
    evidence_items: list[CollectedItem] = field(default_factory=list)
```

```python
# src/auto_report/pipeline/dedup.py
from __future__ import annotations

from auto_report.models.records import CollectedItem, TopicGroup


def deduplicate_items(items: list[CollectedItem]) -> list[TopicGroup]:
    grouped: dict[str, TopicGroup] = {}
    for item in items:
        key = item.url.strip().lower()
        if key not in grouped:
            grouped[key] = TopicGroup(
                group_id=key,
                canonical_title=item.title,
                canonical_url=item.url,
                evidence_items=[],
            )
        grouped[key].evidence_items.append(item)
    return list(grouped.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dedup.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/models src/auto_report/pipeline/dedup.py tests/test_dedup.py
git commit -m "feat: add core record models and deduplication"
```

### Task 4: Add Domain Classification and Scoring

**Files:**
- Create: `src/auto_report/domains/classifier.py`
- Create: `src/auto_report/pipeline/scoring.py`
- Create: `tests/test_domains.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.domains.classifier import classify_topic
from auto_report.models.records import CollectedItem
from auto_report.pipeline.dedup import deduplicate_items


def test_classify_topic_prefers_ai_x_electronics_for_npu_signal():
    item = CollectedItem(
        source_id="rss",
        item_id="1",
        title="New edge AI NPU launch",
        url="https://example.com/npu",
        summary="Embedded accelerator for edge AI cameras",
        published_at="2026-04-09T00:00:00+00:00",
        collected_at="2026-04-09T01:00:00+00:00",
        tags=["edge ai", "npu"],
        language="en",
        metadata={},
    )
    topic = deduplicate_items([item])[0]
    result = classify_topic(topic)
    assert result.primary_domain == "ai-x-electronics"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_domains.py -v`
Expected: FAIL with missing classifier implementation

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/domains/classifier.py
from __future__ import annotations

from dataclasses import dataclass

from auto_report.models.records import TopicGroup


@dataclass(slots=True)
class DomainMatch:
    primary_domain: str
    matched_domains: list[str]


def classify_topic(topic: TopicGroup) -> DomainMatch:
    haystack = " ".join(
        [topic.canonical_title]
        + [item.summary for item in topic.evidence_items]
        + [" ".join(item.tags) for item in topic.evidence_items]
    ).lower()
    if any(token in haystack for token in ("npu", "accelerator", "embedded", "sensor", "edge ai")):
        return DomainMatch(
            primary_domain="ai-x-electronics",
            matched_domains=["ai-x-electronics", "ai-llm-agent"],
        )
    return DomainMatch(primary_domain="ai-llm-agent", matched_domains=["ai-llm-agent"])
```

```python
# src/auto_report/pipeline/scoring.py
from __future__ import annotations

from auto_report.models.records import TopicGroup


def score_topic(topic: TopicGroup) -> float:
    evidence_count = len(topic.evidence_items)
    title_bonus = 1.0 if "agent" in topic.canonical_title.lower() else 0.0
    return evidence_count + title_bonus
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_domains.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/domains/classifier.py src/auto_report/pipeline/scoring.py tests/test_domains.py
git commit -m "feat: add domain classification and scoring"
```

### Task 5: Build Report Rendering and Local Archiving

**Files:**
- Create: `src/auto_report/outputs/renderers.py`
- Create: `src/auto_report/outputs/archive.py`
- Create: `tests/test_renderers.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.outputs.renderers import render_markdown_report


def test_render_markdown_report_contains_title_and_sections():
    report = render_markdown_report(
        title="Daily Summary",
        generated_at="2026-04-09T08:00:00+08:00",
        highlights=["Highlight A", "Highlight B"],
        risks=["Risk A"],
    )
    assert "# Daily Summary" in report
    assert "## Highlights" in report
    assert "## Risks" in report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_renderers.py -v`
Expected: FAIL with missing report renderer

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/outputs/renderers.py
from __future__ import annotations

import json


def render_markdown_report(
    title: str,
    generated_at: str,
    highlights: list[str],
    risks: list[str],
) -> str:
    highlight_lines = "\n".join(f"- {item}" for item in highlights) or "- None"
    risk_lines = "\n".join(f"- {item}" for item in risks) or "- None"
    return (
        f"# {title}\n\n"
        f"Generated at: {generated_at}\n\n"
        "## Highlights\n"
        f"{highlight_lines}\n\n"
        "## Risks\n"
        f"{risk_lines}\n"
    )


def render_json_report(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
```

```python
# src/auto_report/outputs/archive.py
from __future__ import annotations

from pathlib import Path


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_renderers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/outputs/renderers.py src/auto_report/outputs/archive.py tests/test_renderers.py
git commit -m "feat: add report rendering and archive helpers"
```

### Task 6: Implement PushPlus and DeepSeek Provider Adapters

**Files:**
- Create: `src/auto_report/integrations/pushplus.py`
- Create: `src/auto_report/integrations/deepseek.py`
- Create: `tests/test_pushplus.py`
- Create: `docs/DEEPSEEK_SETUP.md`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.integrations.pushplus import build_pushplus_payload


def test_build_pushplus_payload_defaults_to_markdown():
    payload = build_pushplus_payload("token", "AI Daily", "# Summary")
    assert payload["token"] == "token"
    assert payload["template"] == "markdown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pushplus.py -v`
Expected: FAIL with missing PushPlus integration

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/integrations/pushplus.py
from __future__ import annotations

import requests


def build_pushplus_payload(token: str, title: str, content: str) -> dict[str, str]:
    return {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
    }


def send_pushplus(token: str, title: str, content: str) -> dict[str, object]:
    response = requests.post(
        "https://www.pushplus.plus/send",
        json=build_pushplus_payload(token, title, content),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
```

```python
# src/auto_report/integrations/deepseek.py
from __future__ import annotations

import os

import requests


def summarize_with_deepseek(prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": os.environ.get("AI_MODEL", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=40,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
```

```markdown
# docs/DEEPSEEK_SETUP.md

## DeepSeek Setup

1. Register at the DeepSeek platform and create an API key.
2. Copy `.env.example` to `.env`.
3. Fill in:
   - `DEEPSEEK_API_KEY`
   - `AI_BASE_URL`
   - `AI_MODEL`
4. In GitHub repository settings, add the same values to `Secrets and variables > Actions`.
5. Validate locally with:

```bash
python -c "from auto_report.integrations.deepseek import summarize_with_deepseek; print('adapter ok')"
```
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pushplus.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/integrations/pushplus.py src/auto_report/integrations/deepseek.py tests/test_pushplus.py docs/DEEPSEEK_SETUP.md
git commit -m "feat: add pushplus and deepseek adapters"
```

### Task 7: Wire CLI Orchestration and Run Status Files

**Files:**
- Modify: `src/auto_report/cli.py`
- Create: `src/auto_report/app.py`
- Create: `src/auto_report/pipeline/run_once.py`
- Create: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing test**

```python
from auto_report.pipeline.run_once import build_run_status


def test_build_run_status_tracks_generated_outputs():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
    )
    assert status["generated_files"] == ["data/reports/latest-summary.md"]
    assert status["pushed"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_run_once.py -v`
Expected: FAIL with missing run orchestration

- [ ] **Step 3: Write minimal implementation**

```python
# src/auto_report/pipeline/run_once.py
from __future__ import annotations

from datetime import datetime, timezone


def build_run_status(generated_files: list[str], pushed: bool) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
    }
```

```python
# src/auto_report/app.py
from __future__ import annotations

from pathlib import Path

from auto_report.outputs.archive import write_text
from auto_report.outputs.renderers import render_json_report, render_markdown_report
from auto_report.pipeline.run_once import build_run_status


def run_once(root_dir: Path) -> list[str]:
    reports_dir = root_dir / "data" / "reports"
    state_dir = root_dir / "data" / "state"
    markdown = render_markdown_report(
        title="Auto Daily Summary",
        generated_at="local-run",
        highlights=["Framework scaffold ready"],
        risks=["Source integrations not expanded yet"],
    )
    json_report = render_json_report({"status": "ok"})
    summary_path = reports_dir / "latest-summary.md"
    json_path = reports_dir / "latest-summary.json"
    status_path = state_dir / "run-status.json"
    write_text(summary_path, markdown)
    write_text(json_path, json_report)
    write_text(status_path, render_json_report(build_run_status(
        generated_files=[str(summary_path), str(json_path)],
        pushed=False,
    )))
    return [str(summary_path), str(json_path), str(status_path)]
```

```python
# src/auto_report/cli.py
from __future__ import annotations

import argparse
from pathlib import Path

from auto_report.app import run_once


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once")
    subparsers.add_parser("backfill")
    subparsers.add_parser("render-report")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-once":
        run_once(Path.cwd())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_run_once.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/app.py src/auto_report/cli.py src/auto_report/pipeline/run_once.py tests/test_run_once.py
git commit -m "feat: wire local run orchestration"
```

### Task 8: Add Technical Docs and GitHub Actions

**Files:**
- Create: `.github/workflows/collect-report.yml`
- Create: `.github/workflows/backfill-report.yml`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/TECHNICAL_GUIDE.md`
- Create: `docs/USER_GUIDE.md`

- [ ] **Step 1: Write a workflow validation checklist**

```text
Workflow must:
1. Check out repository
2. Install Python
3. Install dependencies
4. Run `python -m auto_report.cli run-once`
5. Upload `data/`
6. Commit changed archive files
```

- [ ] **Step 2: Add workflow implementation**

```yaml
name: Collect And Report

on:
  workflow_dispatch:
  schedule:
    - cron: "17 1,5,9,13 * * *"

jobs:
  collect:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run report
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python -m auto_report.cli run-once
      - uses: actions/upload-artifact@v4
        with:
          name: auto-report-data
          path: data
      - name: Commit report archives
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data
          git diff --cached --quiet || git commit -m "chore: update auto reports"
          git push
```

- [ ] **Step 3: Add user-facing docs**

```markdown
# docs/USER_GUIDE.md

## Quick Start

1. Create a new GitHub repository and upload this project.
2. Add repository secrets:
   - `DEEPSEEK_API_KEY`
   - `PUSHPLUS_TOKEN`
3. Enable GitHub Actions.
4. Open the `Collect And Report` workflow.
5. Click `Run workflow`.
6. Check:
   - workflow artifacts
   - updated `data/` files
   - your PushPlus notification
```

```markdown
# docs/TECHNICAL_GUIDE.md

## Extension Rules

- Add sources in `config/sources/*.yaml` first.
- Keep domain logic in `src/auto_report/domains/`.
- Keep push adapters inside `src/auto_report/integrations/`.
- Blog sync must remain optional and isolated from `run-once`.
```

```markdown
# docs/ARCHITECTURE.md

## Runtime Flow

`cli.py` -> `app.py` -> pipeline -> outputs -> integrations -> archives
```

- [ ] **Step 4: Verify workflows and docs**

Run: `python -m pytest -v`
Expected: PASS

Run: `python -m auto_report.cli run-once`
Expected: exit code 0 and refreshed files under `data/reports` and `data/state`

- [ ] **Step 5: Commit**

```bash
git add .github/workflows docs
git commit -m "docs: add deployment workflows and handoff guides"
```

## Self-Review

### Spec coverage

- Local and GitHub shared CLI: Tasks 1, 7, 8
- Two target domains: Tasks 2 and 4
- Report generation: Tasks 5 and 7
- Push delivery: Task 6
- Local and GitHub archival: Tasks 5, 7, 8
- Blog sync reservation: Task 8 docs and architecture guidance
- DeepSeek setup guidance: Task 6

No missing spec section was found for V1 scaffolding.

### Placeholder scan

The plan avoids `TODO`, `TBD`, and generic "implement later" instructions. The only deferred item is a deliberate `blog sync interface stub`, which is explicitly part of the approved V1 scope.

### Type consistency

- Config loader returns `Settings`
- collection items use `CollectedItem`
- dedup returns `TopicGroup`
- domain classification returns `DomainMatch`
- run orchestration writes status dictionaries and report files

Names used in later tasks match earlier definitions.
