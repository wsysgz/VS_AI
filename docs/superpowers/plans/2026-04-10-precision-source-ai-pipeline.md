# Precision Source And AI Pipeline Implementation Plan

> Latest handoff: `docs/superpowers/status/2026-04-10-stage1-handoff.md`
>
> Execution status on 2026-04-10: first-round local upgrade has been implemented, verified, merged into `main`, and pushed. The next user-requested phase is to continue with original items `3 / 4 / 5`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `VS_AI` locally so it uses repository-local analysis/summarization/forecast pre-reading files, cleaner high-value sources, a staged AI pipeline, and stronger WeChat/Telegram brief rendering while preserving the current `07:00` operating model.

**Architecture:** Keep the current configuration-driven Python package layout, but add three new layers: repository-local AI reading assets, stricter source filtering with curated source definitions, and a staged `analysis -> summary -> forecast` pipeline that can fall back safely at any stage. Rendering remains plain text and Markdown for reliability, but moves from raw lists to structured briefing output tailored by channel.

**Tech Stack:** Python 3.12, pytest, PyYAML, requests, feedparser, python-dotenv, BeautifulSoup, GitHub Actions, DeepSeek-compatible chat completions, PushPlus, Telegram Bot API

---

### Task 1: Add Repository-Local AI Reading Assets And Prompt Loader

**Files:**
- Create: `config/ai_reading/analysis-before.md`
- Create: `config/ai_reading/summary-before.md`
- Create: `config/ai_reading/forecast-before.md`
- Create: `src/auto_report/pipeline/prompt_loader.py`
- Modify: `src/auto_report/settings.py`
- Create: `tests/test_prompt_loader.py`
- Modify: `tests/test_settings.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_prompt_loader.py
from pathlib import Path

from auto_report.pipeline.prompt_loader import load_ai_readings


def test_load_ai_readings_returns_all_stage_texts(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    readings = load_ai_readings(tmp_path)

    assert readings["analysis"] == "analysis-rules"
    assert readings["summary"] == "summary-rules"
    assert readings["forecast"] == "forecast-rules"
```

```python
# tests/test_settings.py
from pathlib import Path

from auto_report.settings import load_settings


def test_load_settings_exposes_ai_reading_paths():
    settings = load_settings(Path.cwd())
    assert settings.ai_reading["analysis"].name == "analysis-before.md"
    assert settings.ai_reading["summary"].name == "summary-before.md"
    assert settings.ai_reading["forecast"].name == "forecast-before.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_prompt_loader.py tests/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError` for `auto_report.pipeline.prompt_loader` and `AttributeError` for missing `ai_reading`

- [ ] **Step 3: Copy the approved pre-reading documents into the repository**

Run: `Copy-Item 'C:\Users\24160\Desktop\毛选-AI分析框架\01-分析前阅读-信息分析与矛盾识别.md' 'D:\GitHub\auto\config\ai_reading\analysis-before.md'; Copy-Item 'C:\Users\24160\Desktop\毛选-AI分析框架\02-总结前阅读-信息综合与提炼.md' 'D:\GitHub\auto\config\ai_reading\summary-before.md'; Copy-Item 'C:\Users\24160\Desktop\毛选-AI分析框架\03-预测前阅读-推演与预测.md' 'D:\GitHub\auto\config\ai_reading\forecast-before.md'`

Expected: three Markdown files exist under `config/ai_reading/`

- [ ] **Step 4: Add the prompt loader and settings wiring**

```python
# src/auto_report/pipeline/prompt_loader.py
from __future__ import annotations

from pathlib import Path


STAGE_FILE_NAMES = {
    "analysis": "analysis-before.md",
    "summary": "summary-before.md",
    "forecast": "forecast-before.md",
}


def load_ai_readings(root_dir: Path) -> dict[str, str]:
    base_dir = root_dir / "config" / "ai_reading"
    readings: dict[str, str] = {}
    for stage, file_name in STAGE_FILE_NAMES.items():
        path = base_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing AI reading asset for {stage}: {path}")
        readings[stage] = path.read_text(encoding="utf-8").strip()
    return readings
```

```python
# src/auto_report/settings.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Settings:
    root_dir: Path
    providers: dict[str, Any]
    domains: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    schedules: dict[str, Any]
    env: dict[str, str] = field(default_factory=dict)
    ai_reading: dict[str, Path] = field(default_factory=dict)
```

```python
# src/auto_report/settings.py inside load_settings(...)
ai_reading = {
    "analysis": resolved_root / "config" / "ai_reading" / "analysis-before.md",
    "summary": resolved_root / "config" / "ai_reading" / "summary-before.md",
    "forecast": resolved_root / "config" / "ai_reading" / "forecast-before.md",
}

return Settings(
    root_dir=resolved_root,
    providers=_read_yaml(config_dir / "providers.yaml"),
    domains=domains,
    sources=sources,
    schedules=_read_yaml(config_dir / "schedules.yaml"),
    env=env,
    ai_reading=ai_reading,
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_prompt_loader.py tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add config/ai_reading src/auto_report/pipeline/prompt_loader.py src/auto_report/settings.py tests/test_prompt_loader.py tests/test_settings.py
git commit -m "feat: add repository ai reading assets"
```

### Task 2: Replace Noisy Sources With Curated High-Value Source Definitions And Filters

**Files:**
- Modify: `config/sources/rss.yaml`
- Modify: `config/sources/github.yaml`
- Modify: `config/sources/websites.yaml`
- Create: `src/auto_report/pipeline/source_filters.py`
- Modify: `src/auto_report/sources/websites.py`
- Modify: `src/auto_report/sources/github.py`
- Modify: `src/auto_report/sources/collector.py`
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_sources.py
from auto_report.pipeline.source_filters import should_keep_candidate
from auto_report.sources.websites import extract_listing_items


def test_should_keep_candidate_drops_navigation_noise():
    source = {
        "include_url_patterns": ["/news/"],
        "exclude_url_patterns": ["/jobs", "/about", "#"],
    }

    assert should_keep_candidate("Anthropic launches X", "https://example.com/news/x", source) is True
    assert should_keep_candidate("Home", "https://example.com/", source) is False
    assert should_keep_candidate("Subscribe", "https://example.com/newsletter", source) is False
    assert should_keep_candidate("Skip to main content", "https://example.com/#content", source) is False


def test_extract_listing_items_uses_selectors_and_filters():
    html = """
    <html><body>
      <a href="/news/release-a">Anthropic launches release A</a>
      <a href="/about">About</a>
      <a href="#content">Skip to main content</a>
    </body></html>
    """
    source = {
        "id": "anthropic-news",
        "url": "https://example.com/news",
        "category_hint": "ai-llm-agent",
        "link_selector": "a",
        "include_url_patterns": ["/news/"],
        "exclude_url_patterns": ["/about", "#"],
    }

    items = extract_listing_items(source, html)

    assert len(items) == 1
    assert items[0].title == "Anthropic launches release A"
    assert items[0].url == "https://example.com/news/release-a"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL with missing `source_filters` module and outdated `extract_listing_items` signature

- [ ] **Step 3: Replace source configuration with curated definitions**

```yaml
# config/sources/rss.yaml
sources:
  - id: huggingface-blog
    enabled: true
    url: https://huggingface.co/blog/feed.xml
    category_hint: ai-llm-agent
    max_items: 12
  - id: openai-news
    enabled: true
    url: https://openai.com/news/rss.xml
    category_hint: ai-llm-agent
    max_items: 8
```

```yaml
# config/sources/github.yaml
sources:
  - id: curated-agent-repos
    enabled: true
    mode: curated_repositories
    category_hint: ai-llm-agent
    repositories:
      - langchain-ai/langgraph
      - vllm-project/vllm
      - ollama/ollama
    max_items: 3
  - id: curated-edge-repos
    enabled: true
    mode: curated_repositories
    category_hint: ai-x-electronics
    repositories:
      - pytorch/executorch
      - alibaba/MNN
      - tenstorrent/tt-metal
    max_items: 3
```

```yaml
# config/sources/websites.yaml
sources:
  - id: anthropic-news
    enabled: true
    mode: article_listing
    url: https://www.anthropic.com/news
    category_hint: ai-llm-agent
    max_items: 8
    link_selector: "a[href^='/news/']"
    include_url_patterns: ["/news/"]
    exclude_url_patterns: ["/jobs", "/about", "#"]
  - id: deepseek-updates
    enabled: true
    mode: article_listing
    url: https://api-docs.deepseek.com/news/news
    category_hint: ai-llm-agent
    max_items: 8
    link_selector: "a[href*='/news/']"
    include_url_patterns: ["/news/"]
    exclude_url_patterns: ["#"]
  - id: qwen-blog
    enabled: true
    mode: article_listing
    url: https://qwenlm.github.io/blog/
    category_hint: ai-llm-agent
    max_items: 6
    link_selector: "a[href*='/blog/']"
    include_url_patterns: ["/blog/"]
    exclude_url_patterns: ["#"]
  - id: moonshot-blog
    enabled: true
    mode: article_listing
    url: https://platform.moonshot.cn/blog/posts/
    category_hint: ai-llm-agent
    max_items: 6
    link_selector: "a[href*='/blog/posts/']"
    include_url_patterns: ["/blog/posts/"]
    exclude_url_patterns: ["#"]
  - id: arm-news
    enabled: true
    mode: article_listing
    url: https://newsroom.arm.com/news
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href*='/news/']"
    include_url_patterns: ["/news/"]
    exclude_url_patterns: ["/about", "#"]
  - id: qualcomm-onq
    enabled: true
    mode: article_listing
    url: https://www.qualcomm.com/news/onq
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href*='/news/onq/']"
    include_url_patterns: ["/news/onq/"]
    exclude_url_patterns: ["/support", "#"]
```

- [ ] **Step 4: Add filter helpers and new extractors**

```python
# src/auto_report/pipeline/source_filters.py
from __future__ import annotations


NOISE_TITLES = {
    "home",
    "subscribe",
    "pricing",
    "docs",
    "jobs",
    "about",
    "skip to main content",
}


def should_keep_candidate(title: str, url: str, source: dict[str, object]) -> bool:
    normalized_title = title.strip().lower()
    normalized_url = url.strip().lower()
    if not normalized_title or normalized_title in NOISE_TITLES or len(normalized_title) < 8:
        return False
    if normalized_url.endswith("#") or "#content" in normalized_url:
        return False

    include_patterns = [str(item).lower() for item in source.get("include_url_patterns", [])]
    exclude_patterns = [str(item).lower() for item in source.get("exclude_url_patterns", [])]

    if include_patterns and not any(pattern in normalized_url for pattern in include_patterns):
        return False
    if any(pattern in normalized_url for pattern in exclude_patterns):
        return False
    return True
```

```python
# src/auto_report/sources/websites.py
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from auto_report.models.records import CollectedItem
from auto_report.pipeline.source_filters import should_keep_candidate


def extract_listing_items(source: dict[str, object], html: str) -> list[CollectedItem]:
    soup = BeautifulSoup(html, "html.parser")
    collected_at = datetime.now(timezone.utc).isoformat()
    page_url = str(source["url"])
    selector = str(source.get("link_selector", "a[href]"))
    category_hint = str(source.get("category_hint", ""))

    items: list[CollectedItem] = []
    for index, anchor in enumerate(soup.select(selector)):
        href = anchor.get("href")
        title = anchor.get_text(" ", strip=True)
        if not href:
            continue
        url = urljoin(page_url, href)
        if not should_keep_candidate(title, url, source):
            continue
        items.append(
            CollectedItem(
                source_id=str(source["id"]),
                item_id=f"{source['id']}:{index}",
                title=title,
                url=url,
                summary="",
                published_at=collected_at,
                collected_at=collected_at,
                tags=[category_hint] if category_hint else [],
                language="unknown",
                metadata={"page_url": page_url},
            )
        )
    return items
```

```python
# src/auto_report/sources/github.py
from __future__ import annotations

from datetime import datetime, timezone

from auto_report.models.records import CollectedItem


def normalize_github_repository_detail(
    source_id: str,
    payload: dict[str, object],
    category_hint: str,
) -> CollectedItem | None:
    collected_at = datetime.now(timezone.utc).isoformat()
    title = str(payload.get("full_name", "")).strip()
    url = str(payload.get("html_url", "")).strip()
    if not title or not url:
        return None
    tags = [str(tag) for tag in payload.get("topics", [])]
    if category_hint and category_hint not in tags:
        tags.append(category_hint)
    return CollectedItem(
        source_id=source_id,
        item_id=f"{source_id}:{title}",
        title=title,
        url=url,
        summary=str(payload.get("description", "") or "").strip(),
        published_at=str(payload.get("updated_at", collected_at)),
        collected_at=collected_at,
        tags=tags,
        language=str(payload.get("language", "") or "unknown"),
        metadata={"stars": int(payload.get("stargazers_count", 0) or 0)},
    )
```

```python
# src/auto_report/sources/collector.py inside _collect_github(...)
for source in settings.sources.get("github", {}).get("sources", []):
    if not source.get("enabled", False):
        continue
    if source.get("mode") != "curated_repositories":
        continue
    repositories = [str(item).strip() for item in source.get("repositories", [])]
    for full_name in repositories[: int(source.get("max_items", len(repositories) or 0))]:
        response = requests.get(
            f"https://api.github.com/repos/{full_name}",
            timeout=20,
            headers=headers,
        )
        response.raise_for_status()
        item = normalize_github_repository_detail(
            source_id=str(source["id"]),
            payload=response.json(),
            category_hint=str(source.get("category_hint", "")),
        )
        if item is not None:
            items.append(item)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add config/sources src/auto_report/pipeline/source_filters.py src/auto_report/sources/websites.py src/auto_report/sources/github.py src/auto_report/sources/collector.py tests/test_sources.py
git commit -m "feat: curate sources and add source filters"
```

### Task 3: Build Rich Topic Candidates Before AI Stages

**Files:**
- Modify: `src/auto_report/models/records.py`
- Create: `src/auto_report/pipeline/topic_builder.py`
- Modify: `src/auto_report/pipeline/analysis.py`
- Create: `tests/test_topic_builder.py`
- Modify: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_topic_builder.py
from auto_report.models.records import CollectedItem
from auto_report.pipeline.topic_builder import build_topic_candidates


def test_build_topic_candidates_merges_source_ids_and_summaries():
    items = [
        CollectedItem(
            source_id="openai-news",
            item_id="1",
            title="OpenAI launches feature",
            url="https://example.com/feature",
            summary="OpenAI launched feature A",
            published_at="2026-04-10T00:00:00+00:00",
            collected_at="2026-04-10T00:01:00+00:00",
            tags=["ai-llm-agent"],
            language="en",
            metadata={},
        ),
        CollectedItem(
            source_id="anthropic-news",
            item_id="2",
            title="OpenAI launches feature",
            url="https://example.com/feature",
            summary="Independent confirmation of feature A",
            published_at="2026-04-10T00:02:00+00:00",
            collected_at="2026-04-10T00:03:00+00:00",
            tags=["ai-llm-agent"],
            language="en",
            metadata={},
        ),
    ]

    candidates = build_topic_candidates(items)

    assert len(candidates) == 1
    assert candidates[0].evidence_count == 2
    assert candidates[0].source_ids == ["anthropic-news", "openai-news"]
    assert "OpenAI launched feature A" in candidates[0].evidence_snippets
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_topic_builder.py tests/test_analysis.py -v`
Expected: FAIL with missing `build_topic_candidates` and missing richer analysis inputs

- [ ] **Step 3: Add topic candidate model and builder**

```python
# src/auto_report/models/records.py
from dataclasses import dataclass, field


@dataclass(slots=True)
class TopicCandidate:
    topic_id: str
    title: str
    url: str
    primary_domain: str
    matched_domains: list[str]
    evidence_count: int
    source_ids: list[str]
    tags: list[str]
    evidence_snippets: list[str]
```

```python
# src/auto_report/pipeline/topic_builder.py
from __future__ import annotations

from auto_report.domains.classifier import classify_topic
from auto_report.models.records import CollectedItem, TopicCandidate
from auto_report.pipeline.dedup import deduplicate_items


def build_topic_candidates(items: list[CollectedItem]) -> list[TopicCandidate]:
    topics = deduplicate_items(items)
    candidates: list[TopicCandidate] = []
    for topic in topics:
        domain_match = classify_topic(topic)
        evidence_snippets = [
            item.summary.strip()
            for item in topic.evidence_items
            if item.summary.strip()
        ][:4]
        candidates.append(
            TopicCandidate(
                topic_id=topic.group_id,
                title=topic.canonical_title,
                url=topic.canonical_url,
                primary_domain=domain_match.primary_domain,
                matched_domains=domain_match.matched_domains,
                evidence_count=len(topic.evidence_items),
                source_ids=sorted({item.source_id for item in topic.evidence_items}),
                tags=sorted({tag for item in topic.evidence_items for tag in item.tags if tag}),
                evidence_snippets=evidence_snippets,
            )
        )
    return candidates
```

```python
# src/auto_report/pipeline/analysis.py inside build_report_package(...)
from auto_report.pipeline.topic_builder import build_topic_candidates


topic_candidates = build_topic_candidates(items)
summary_payload["meta"]["total_topics"] = len(topic_candidates)
```

- [ ] **Step 4: Update the analysis test to assert topic metadata exists**

```python
# tests/test_analysis.py
assert package.summary_payload["meta"]["total_topics"] == 2
assert package.summary_payload["signals"][0]["evidence_count"] >= 1
assert "ai-llm-agent" in package.domain_payloads
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_topic_builder.py tests/test_analysis.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/models/records.py src/auto_report/pipeline/topic_builder.py src/auto_report/pipeline/analysis.py tests/test_topic_builder.py tests/test_analysis.py
git commit -m "feat: add rich topic candidates"
```

### Task 4: Implement The Staged AI Analysis, Summary, And Forecast Pipeline With Safe Fallbacks

**Files:**
- Modify: `src/auto_report/integrations/deepseek.py`
- Create: `src/auto_report/pipeline/ai_pipeline.py`
- Modify: `src/auto_report/pipeline/analysis.py`
- Create: `tests/test_ai_pipeline.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ai_pipeline.py
from auto_report.models.records import TopicCandidate
from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline


def test_run_staged_ai_pipeline_returns_structured_outputs(monkeypatch):
    candidate = TopicCandidate(
        topic_id="topic-1",
        title="Agent benchmark release",
        url="https://example.com/agent",
        primary_domain="ai-llm-agent",
        matched_domains=["ai-llm-agent"],
        evidence_count=2,
        source_ids=["openai-news", "anthropic-news"],
        tags=["agent", "benchmark"],
        evidence_snippets=["Release notes", "Independent commentary"],
    )

    responses = iter(
        [
            '{"facts":["Release published"],"contradictions":["speed vs reliability"],"primary_contradiction":"speed vs reliability","core_insight":"evaluation is becoming central","confidence":"medium"}',
            '{"one_line_core":"Agent evaluation becomes a core battleground","executive_summary":["A","B"],"key_points":[{"title":"Signal","why_it_matters":"Matters"}],"key_insights":["Insight"],"limitations":["Need verification"],"actions":["Track benchmarks"]}',
            '{"most_likely_case":"benchmark competition intensifies","best_case":"better reliability","worst_case":"benchmark theater","key_variables":["real deployment"],"forecast_conclusion":"watch evaluation quality","confidence":"medium"}',
        ]
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.summarize_with_deepseek",
        lambda prompt: next(responses),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "ok"
    assert outputs["summary"]["one_line_core"].startswith("Agent evaluation")
    assert outputs["forecast"]["most_likely_case"] == "benchmark competition intensifies"
```

```python
# tests/test_ai_pipeline.py
def test_run_staged_ai_pipeline_falls_back_when_ai_errors(monkeypatch):
    candidate = TopicCandidate(
        topic_id="topic-1",
        title="Edge NPU launch",
        url="https://example.com/npu",
        primary_domain="ai-x-electronics",
        matched_domains=["ai-x-electronics"],
        evidence_count=1,
        source_ids=["arm-news"],
        tags=["npu"],
        evidence_snippets=["Edge NPU release"],
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.summarize_with_deepseek",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "fallback"
    assert outputs["stage_status"]["summary"] == "fallback"
    assert outputs["stage_status"]["forecast"] == "fallback"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ai_pipeline.py -v`
Expected: FAIL with missing `run_staged_ai_pipeline`

- [ ] **Step 3: Extend the DeepSeek adapter to support stage calls**

```python
# src/auto_report/integrations/deepseek.py
from __future__ import annotations

from typing import Any
import os

import requests


def build_deepseek_payload(prompt: str) -> dict[str, Any]:
    return {
        "model": os.environ.get("AI_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(os.environ.get("AI_TEMPERATURE", "0.2")),
    }


def summarize_with_deepseek(prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=build_deepseek_payload(prompt),
        timeout=40,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
```

- [ ] **Step 4: Add the staged AI pipeline with explicit parsers and fallbacks**

```python
# src/auto_report/pipeline/ai_pipeline.py
from __future__ import annotations

import json

from auto_report.integrations.deepseek import summarize_with_deepseek
from auto_report.models.records import TopicCandidate


def _parse_json_block(text: str) -> dict[str, object]:
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object")
    return data


def _fallback_analysis(candidate: TopicCandidate) -> dict[str, object]:
    return {
        "title": candidate.title,
        "url": candidate.url,
        "primary_domain": candidate.primary_domain,
        "facts": candidate.evidence_snippets or [f"Collected {candidate.evidence_count} evidence items"],
        "contradictions": ["signal strength vs evidence completeness"],
        "primary_contradiction": "signal strength vs evidence completeness",
        "core_insight": f"{candidate.title} is relevant but needs deeper verification.",
        "confidence": "low",
    }


def _fallback_summary(analyses: list[dict[str, object]]) -> dict[str, object]:
    titles = [str(item.get("title", "未命名主题")) for item in analyses[:3]]
    return {
        "one_line_core": "本轮先按规则模式输出，AI 总结阶段已回退。",
        "executive_summary": [f"重点关注：{title}" for title in titles] or ["暂无足够主题"],
        "key_points": [{"title": title, "why_it_matters": "需要继续观察。"} for title in titles],
        "key_insights": ["当前输出来自规则回退路径。"],
        "limitations": ["AI 总结阶段失败，请结合原始链接复核。"],
        "actions": ["优先检查来源页面与模型响应。"],
    }


def _fallback_forecast(summary: dict[str, object]) -> dict[str, object]:
    return {
        "best_case": "后续轮次恢复完整预测输出。",
        "worst_case": "本轮仅保留事实与总结，不输出可靠预测。",
        "most_likely_case": "近期继续观察主题是否形成跨源重复出现。",
        "key_variables": ["cross_source_repetition", "official_release_follow_up"],
        "forecast_conclusion": "本轮预测阶段已回退，暂不提供强结论。",
        "confidence": "low",
    }


def run_staged_ai_pipeline(
    candidates: list[TopicCandidate],
    ai_readings: dict[str, str],
    ai_enabled: bool,
) -> dict[str, object]:
    analyses: list[dict[str, object]] = []
    stage_status = {"analysis": "skipped", "summary": "skipped", "forecast": "skipped"}

    if ai_enabled:
        try:
            for candidate in candidates:
                prompt = "\n\n".join(
                    [
                        ai_readings["analysis"],
                        json.dumps(candidate.__dict__, ensure_ascii=False, indent=2),
                        "请仅输出 JSON 对象。",
                    ]
                )
                analysis = _parse_json_block(summarize_with_deepseek(prompt))
                analysis.setdefault("title", candidate.title)
                analysis.setdefault("url", candidate.url)
                analysis.setdefault("primary_domain", candidate.primary_domain)
                analyses.append(analysis)
            stage_status["analysis"] = "ok"
        except Exception:
            analyses = [_fallback_analysis(candidate) for candidate in candidates]
            stage_status["analysis"] = "fallback"
    else:
        analyses = [_fallback_analysis(candidate) for candidate in candidates]
        stage_status["analysis"] = "fallback"

    if ai_enabled and stage_status["analysis"] == "ok":
        try:
            prompt = "\n\n".join(
                [ai_readings["summary"], json.dumps(analyses, ensure_ascii=False, indent=2), "请仅输出 JSON 对象。"]
            )
            summary = _parse_json_block(summarize_with_deepseek(prompt))
            stage_status["summary"] = "ok"
        except Exception:
            summary = _fallback_summary(analyses)
            stage_status["summary"] = "fallback"
    else:
        summary = _fallback_summary(analyses)
        stage_status["summary"] = "fallback"

    if ai_enabled and stage_status["summary"] == "ok":
        try:
            prompt = "\n\n".join(
                [ai_readings["forecast"], json.dumps({"analyses": analyses, "summary": summary}, ensure_ascii=False, indent=2), "请仅输出 JSON 对象。"]
            )
            forecast = _parse_json_block(summarize_with_deepseek(prompt))
            stage_status["forecast"] = "ok"
        except Exception:
            forecast = _fallback_forecast(summary)
            stage_status["forecast"] = "fallback"
    else:
        forecast = _fallback_forecast(summary)
        stage_status["forecast"] = "fallback"

    return {
        "analyses": analyses,
        "summary": summary,
        "forecast": forecast,
        "stage_status": stage_status,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ai_pipeline.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/integrations/deepseek.py src/auto_report/pipeline/ai_pipeline.py tests/test_ai_pipeline.py
git commit -m "feat: add staged ai pipeline"
```

### Task 5: Integrate The Staged AI Outputs Into Report Packaging, Rendering, And Run Status

**Files:**
- Modify: `src/auto_report/pipeline/analysis.py`
- Modify: `src/auto_report/outputs/renderers.py`
- Modify: `src/auto_report/app.py`
- Modify: `src/auto_report/pipeline/run_once.py`
- Modify: `tests/test_renderers.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_renderers.py
from auto_report.outputs.renderers import render_text_notification


def test_render_text_notification_uses_morning_brief_shape():
    text = render_text_notification(
        title="AI情报早报 | 04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
            "key_points": [
                {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
                {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
            ],
            "forecast": {"most_likely_case": "短期继续围绕评估与部署演进"},
            "limitations": ["部分信号仍需复核"],
        },
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "今日一句话：" in text
    assert "【主线】评估框架增加" in text
    assert "【提醒】部分信号仍需复核" in text
```

```python
# tests/test_run_once.py
def test_build_run_status_includes_stage_status_and_source_counts():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        stage_status={"analysis": "ok", "summary": "fallback", "forecast": "fallback"},
        source_stats={"collected_items": 12, "filtered_topics": 5},
    )

    assert status["stage_status"]["analysis"] == "ok"
    assert status["source_stats"]["filtered_topics"] == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_renderers.py tests/test_run_once.py -v`
Expected: FAIL because the renderer and run status shape are still first-generation

- [ ] **Step 3: Upgrade report packaging to carry staged outputs**

```python
# src/auto_report/pipeline/analysis.py
from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline
from auto_report.pipeline.prompt_loader import load_ai_readings
from auto_report.pipeline.topic_builder import build_topic_candidates


def build_report_package(
    settings: Settings,
    items: list[CollectedItem],
    diagnostics: list[str],
) -> ReportPackage:
    topic_candidates = build_topic_candidates(items)
    ai_outputs = run_staged_ai_pipeline(
        candidates=topic_candidates,
        ai_readings=load_ai_readings(settings.root_dir),
        ai_enabled=bool(settings.env["DEEPSEEK_API_KEY"]),
    )

    summary_payload = {
        "meta": {
            "generated_at": "",
            "timezone": settings.env["AUTO_TIMEZONE"],
            "total_items": len(items),
            "total_topics": len(topic_candidates),
        },
        "one_line_core": ai_outputs["summary"]["one_line_core"],
        "executive_summary": ai_outputs["summary"]["executive_summary"],
        "key_points": ai_outputs["summary"]["key_points"],
        "key_insights": ai_outputs["summary"]["key_insights"],
        "limitations": ai_outputs["summary"]["limitations"] + diagnostics,
        "actions": ai_outputs["summary"]["actions"],
        "analyses": ai_outputs["analyses"],
        "forecast": ai_outputs["forecast"],
        "stage_status": ai_outputs["stage_status"],
    }
```

```python
# src/auto_report/pipeline/analysis.py domain payload section
domain_payloads[domain_key] = {
    "title": domain.get("title", domain_key),
    "one_line_core": summary_payload["one_line_core"],
    "key_points": summary_payload["key_points"][:2],
    "limitations": summary_payload["limitations"],
    "forecast": summary_payload["forecast"],
}
```

- [ ] **Step 4: Upgrade the renderers and run status**

```python
# src/auto_report/outputs/renderers.py
def render_markdown_report(title: str, generated_at: str, payload: dict[str, object]) -> str:
    executive_summary = "\n".join(f"- {item}" for item in payload.get("executive_summary", [])) or "- 暂无"
    key_insights = "\n".join(f"- {item}" for item in payload.get("key_insights", [])) or "- 暂无"
    limitations = "\n".join(f"- {item}" for item in payload.get("limitations", [])) or "- 暂无"
    forecast = payload.get("forecast", {})
    analyses = payload.get("analyses", [])

    lines = [
        f"# {title}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 一句话核心",
        str(payload.get("one_line_core", "暂无核心判断")),
        "",
        "## 执行摘要",
        executive_summary,
        "",
        "## 关键洞察",
        key_insights,
        "",
        "## 主题分析",
    ]

    for analysis in analyses[:6]:
        lines.extend(
            [
                f"### {analysis.get('title', '未命名主题')}",
                f"- 主领域：{analysis.get('primary_domain', 'unknown')}",
                f"- 主要矛盾：{analysis.get('primary_contradiction', '待补充')}",
                f"- 核心洞察：{analysis.get('core_insight', '待补充')}",
                f"- 置信度：{analysis.get('confidence', 'low')}",
                f"- 链接：{analysis.get('url', '')}",
                "",
            ]
        )

    lines.extend(
        [
            "## 短期预测",
            f"- 最可能：{forecast.get('most_likely_case', '暂无')}",
            f"- 结论：{forecast.get('forecast_conclusion', '暂无')}",
            "",
            "## 局限性",
            limitations,
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_text_notification(title: str, generated_at: str, payload: dict[str, object], detail_url: str) -> str:
    lines = [
        title,
        f"生成时间：{generated_at}",
        "今日一句话：",
        str(payload.get("one_line_core", "暂无核心判断")),
        "今日三点：",
    ]
    for point in payload.get("key_points", [])[:3]:
        lines.append(f"【主线】{point.get('title', '未命名要点')}")
        lines.append(f"【影响】{point.get('why_it_matters', '需要继续观察')}")
    limitations = payload.get("limitations", [])
    if limitations:
        lines.append(f"【提醒】{limitations[0]}")
    forecast = payload.get("forecast", {})
    lines.append(f"【观察】{forecast.get('most_likely_case', '暂无趋势提示')}")
    lines.append("详情链接：")
    lines.append(detail_url)
    return "\n".join(lines)
```

```python
# src/auto_report/pipeline/run_once.py
from datetime import datetime, timezone
from typing import Any


def build_run_status(
    generated_files: list[str],
    pushed: bool,
    push_channel: str = "",
    push_response: dict[str, Any] | None = None,
    stage_status: dict[str, str] | None = None,
    source_stats: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
        "push_channel": push_channel,
        "push_response": push_response or {},
        "stage_status": stage_status or {},
        "source_stats": source_stats or {},
    }
```

```python
# src/auto_report/app.py inside render_reports() and run_once()
package = build_report_package(settings, items, diagnostics)
summary_markdown = render_markdown_report(
    title="自动情报快报",
    generated_at=generated_at,
    payload=package.summary_payload,
)

status = build_run_status(
    generated_files=generated_files,
    pushed=pushed,
    push_channel=push_channel,
    push_response=push_response,
    stage_status=package.summary_payload.get("stage_status", {}),
    source_stats={
        "collected_items": len(items),
        "filtered_topics": int(package.summary_payload["meta"]["total_topics"]),
    },
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_renderers.py tests/test_run_once.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/pipeline/analysis.py src/auto_report/outputs/renderers.py src/auto_report/app.py src/auto_report/pipeline/run_once.py tests/test_renderers.py tests/test_run_once.py
git commit -m "feat: integrate staged ai outputs into reports"
```

### Task 6: Refresh User-Facing Documentation And Verify The Full Local Flow

**Files:**
- Modify: `README.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/TECHNICAL_GUIDE.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Update the README operating model**

```markdown
# VS_AI

AI 情报采集与分析系统。

当前第一轮升级后，系统的主流程是：

`精选采集 -> 去噪过滤 -> 主题归并 -> 分析 -> 总结 -> 预测 -> 微信/Telegram 渲染 -> 归档/推送`

当前自动化规则：

- 北京时间 `07:00` 每天自动生成并推送 `1` 条综合总报
- 微信走短摘要通道
- Telegram 走完整简报通道
- 三份 AI 底层逻辑文件保存在仓库 `config/ai_reading/`
- 本地先验证，再推送到仓库自动运行
```

- [ ] **Step 2: Update the user and technical guides**

```markdown
# docs/USER_GUIDE.md

## 本轮升级后的关键变化

- 信息源改为少而精的官方/精选来源
- 系统会在运行时读取：
  - `config/ai_reading/analysis-before.md`
  - `config/ai_reading/summary-before.md`
  - `config/ai_reading/forecast-before.md`
- 如果 AI 某阶段失败，系统会回退而不会整轮报错中断
- `data/state/run-status.json` 现在会记录分析/总结/预测阶段状态
```

```markdown
# docs/TECHNICAL_GUIDE.md

## 新的 AI 执行链路

1. `collector.py` 采集精选来源
2. `source_filters.py` 去除网页噪音
3. `topic_builder.py` 构建主题候选
4. `ai_pipeline.py` 依次运行分析、总结、预测
5. `renderers.py` 输出微信短报与 Telegram 全文

## 回退策略

- 分析失败：主题级规则回退
- 总结失败：总报级规则回退
- 预测失败：仅保留事实与总结，不输出强预测
```

```markdown
# docs/ARCHITECTURE.md

## 当前执行链路

`cli.py` -> `app.py` -> `settings.py` -> `sources/` -> `pipeline/source_filters.py` -> `pipeline/topic_builder.py` -> `pipeline/ai_pipeline.py` -> `outputs/` -> `integrations/` -> `data/`
```

- [ ] **Step 3: Run the complete verification sequence**

Run: `python -m pytest -q`
Expected: PASS

Run: `python -m auto_report.cli run-once`
Expected: exit code `0`

Run: `Get-Content -Raw 'D:\GitHub\auto\data\reports\latest-summary.md'`
Expected: contains `## 一句话核心`, `## 执行摘要`, and `## 短期预测`

Run: `Get-Content -Raw 'D:\GitHub\auto\data\state\run-status.json'`
Expected: contains `stage_status` and `source_stats`

- [ ] **Step 4: Inspect for noise regression**

Run: `Get-Content -Raw 'D:\GitHub\auto\data\reports\latest-summary.json'`
Expected: does not surface obvious navigation junk such as `Home`, `Subscribe`, or `Skip to main content` in top topics

- [ ] **Step 5: Commit**

```bash
git add README.md docs/USER_GUIDE.md docs/TECHNICAL_GUIDE.md docs/ARCHITECTURE.md
git commit -m "docs: describe staged ai briefing pipeline"
```

## Self-Review

### Spec coverage

- Repository-local methodology Markdown files: Task 1
- Curated high-value sources and noise filtering: Task 2
- Richer topic candidates before AI: Task 3
- Staged `analysis -> summary -> forecast` AI flow: Task 4
- Channel-specific structured rendering and run status: Task 5
- Docs and local verification before automation rollout: Task 6

No approved requirement from the first upgrade spec is left without a task.

### Placeholder scan

- No task contains `TODO`, `TBD`, or “implement later”.
- Each task lists exact file paths.
- Each test and implementation step includes concrete code or concrete commands.
- Verification steps specify expected outcomes.

### Type consistency

- `Settings.ai_reading` is a `dict[str, Path]`
- `TopicCandidate` is introduced before the staged AI pipeline uses it
- staged AI outputs remain `dict[str, object]` throughout the pipeline and renderers
- `build_run_status` explicitly accepts `stage_status` and `source_stats`

The names and shapes used in later tasks match the earlier task definitions.
