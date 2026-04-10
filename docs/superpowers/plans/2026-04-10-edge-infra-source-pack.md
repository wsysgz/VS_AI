# Edge And Infra Source Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a compact, official, engineering-useful source pack for `AI × 电子信息 / 边缘 / 基础设施` so the report gains stronger edge and deployment signal quality.

**Architecture:** Keep the current source collection pipeline intact, but extend `config/sources/websites.yaml` with a first batch of official edge and infra sources and strengthen title/url filtering to reject event and marketing noise. Verification focuses on proving that useful deployment-oriented posts survive while low-value titles are filtered out.

**Tech Stack:** Python 3.14, pytest, YAML source configs, BeautifulSoup-based website collectors

---

### Task 1: Add Tests For Edge And Infra Source Filtering

**Files:**
- Modify: `tests/test_sources.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_should_keep_candidate_drops_webinar_and_event_noise():
    source = {
        "include_url_patterns": ["/embedded/", "/edge/", "/litert/", "/openvino/", "/genai/"],
        "exclude_url_patterns": ["/webinar", "/event", "/register"],
        "exclude_title_patterns": ["webinar", "event", "register", "ebook", "white paper"],
    }

    assert should_keep_candidate(
        "Jetson Orin brings faster edge inference",
        "https://developer.nvidia.com/blog/jetson-orin-edge-inference",
        source,
    ) is True
    assert should_keep_candidate(
        "Register for our Edge AI Webinar",
        "https://example.com/edge/webinar",
        source,
    ) is False
    assert should_keep_candidate(
        "OpenVINO event for developers",
        "https://example.com/openvino/event-2026",
        source,
    ) is False


def test_extract_listing_items_supports_title_include_patterns():
    html = """
    <html><body>
      <a href="/blog/jetson-edge-ai">
        <h3>Jetson edge AI pipeline update</h3>
      </a>
      <a href="/blog/company-update">
        <h3>Company update for partners</h3>
      </a>
    </body></html>
    """

    items = extract_listing_items(
        {
            "id": "nvidia-embedded",
            "url": "https://developer.nvidia.com/blog",
            "category_hint": "ai-x-electronics",
            "link_selector": "a",
            "include_url_patterns": ["/blog/"],
            "include_title_patterns": ["jetson", "edge", "embedded", "tensorrt"],
            "exclude_title_patterns": ["partner", "event", "webinar"],
        },
        html,
    )

    assert [item.title for item in items] == ["Jetson edge AI pipeline update"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_sources.py -v`
Expected: FAIL because current noise filtering does not reject webinar/event titles and listing extraction does not yet prove the new rules

- [ ] **Step 3: Write the minimal implementation**

```python
# src/auto_report/pipeline/source_filters.py
NOISE_TITLES = {
    "home",
    "subscribe",
    "pricing",
    "docs",
    "jobs",
    "about",
    "skip to main content",
}

NOISE_TITLE_PATTERNS = {
    "webinar",
    "register",
    "event",
    "ebook",
    "white paper",
    "press release",
    "partner",
    "sponsor",
}


def should_keep_candidate(title: str, url: str, source: dict[str, object]) -> bool:
    normalized_title = title.strip().lower()
    normalized_url = url.strip().lower()

    if not normalized_title or normalized_title in NOISE_TITLES or len(normalized_title) < 8:
        return False
    if any(pattern in normalized_title for pattern in NOISE_TITLE_PATTERNS):
        return False
    if normalized_url.endswith("#") or "#content" in normalized_url:
        return False

    include_patterns = [str(item).lower() for item in source.get("include_url_patterns", [])]
    exclude_patterns = [str(item).lower() for item in source.get("exclude_url_patterns", [])]
    include_title_patterns = [str(item).lower() for item in source.get("include_title_patterns", [])]
    exclude_title_patterns = [str(item).lower() for item in source.get("exclude_title_patterns", [])]

    if include_patterns and not any(pattern in normalized_url for pattern in include_patterns):
        return False
    if any(pattern in normalized_url for pattern in exclude_patterns):
        return False
    if include_title_patterns and not any(pattern in normalized_title for pattern in include_title_patterns):
        return False
    if any(pattern in normalized_title for pattern in exclude_title_patterns):
        return False
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_sources.py src/auto_report/pipeline/source_filters.py
git commit -m "test: cover edge source filtering rules"
```

### Task 2: Add The First Edge And Infra Source Pack

**Files:**
- Modify: `config/sources/websites.yaml`

- [ ] **Step 1: Write the failing config-oriented test**

```python
from pathlib import Path

from auto_report.settings import load_settings


def test_load_settings_includes_edge_infra_source_pack():
    settings = load_settings(Path.cwd())
    website_sources = settings.sources["websites"]["sources"]
    source_ids = {source["id"] for source in website_sources}

    assert "nvidia-embedded" in source_ids
    assert "google-ai-edge" in source_ids
    assert "openvino-blog" in source_ids
    assert "nxp-edge-ai" in source_ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_settings.py tests/test_sources.py -v`
Expected: FAIL because the new source ids are not present yet

- [ ] **Step 3: Write the minimal implementation**

```yaml
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
    url: https://api-docs.deepseek.com/updates/
    category_hint: ai-llm-agent
    max_items: 8
    link_selector: "nav.menu a[href^='/news/']"
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
    url: https://platform.moonshot.cn/blog
    category_hint: ai-llm-agent
    max_items: 6
    link_selector: "div.post-item a[href^='/blog/posts/']"
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
  - id: nvidia-embedded
    enabled: true
    mode: article_listing
    url: https://developer.nvidia.com/blog
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href*='/blog/']"
    include_url_patterns: ["/blog/"]
    include_title_patterns: ["jetson", "embedded", "edge", "tensorrt", "robotics"]
    exclude_url_patterns: ["#"]
    exclude_title_patterns: ["webinar", "event", "partner", "register"]
  - id: google-ai-edge
    enabled: true
    mode: article_listing
    url: https://developers.googleblog.com/
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href*='developers.googleblog.com/']"
    include_url_patterns: ["developers.googleblog.com/"]
    include_title_patterns: ["litert", "ai edge", "on-device", "npu", "edge ai"]
    exclude_url_patterns: ["#"]
    exclude_title_patterns: ["event", "register", "partner"]
  - id: openvino-blog
    enabled: true
    mode: article_listing
    url: https://blog.openvino.ai/
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href]"
    include_url_patterns: ["blog.openvino.ai"]
    include_title_patterns: ["openvino", "npu", "edge", "ai pc", "inference"]
    exclude_url_patterns: ["#", "/tag/"]
    exclude_title_patterns: ["event", "webinar", "register"]
  - id: nxp-edge-ai
    enabled: true
    mode: article_listing
    url: https://www.nxp.com/company/about-nxp/smarter-world-blog
    category_hint: ai-x-electronics
    max_items: 6
    link_selector: "a[href*='/company/about-nxp/smarter-world-blog/']"
    include_url_patterns: ["/company/about-nxp/smarter-world-blog/"]
    include_title_patterns: ["edge ai", "genai", "npu", "embedded", "i.mx", "eiq"]
    exclude_url_patterns: ["#"]
    exclude_title_patterns: ["event", "webinar", "partner", "register"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_settings.py tests/test_sources.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add config/sources/websites.yaml tests/test_settings.py
git commit -m "feat: add edge and infra source pack"
```

### Task 3: Verify The Expanded Source Pack End-To-End

**Files:**
- No code changes required unless verification reveals a concrete source rule issue

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 2: Run the full local flow without push**

Run: `$env:AUTO_PUSH_ENABLED='false'; python -m auto_report.cli run-once`
Expected: exit code `0`

- [ ] **Step 3: Inspect the generated summary JSON for edge signal presence**

Run: `(Get-Content -Raw 'D:\GitHub\worktrees\auto\feature-edge-source-pack\data\reports\latest-summary.json' | ConvertFrom-Json).signals | Group-Object primary_domain | Select-Object Name,Count`
Expected: `ai-x-electronics` count is meaningfully above the previous `3`-topic baseline

- [ ] **Step 4: Inspect the generated summary JSON for obvious noise**

Run: `Get-Content -Raw 'D:\GitHub\worktrees\auto\feature-edge-source-pack\data\reports\latest-summary.json'`
Expected: top signals do not prominently contain webinar/event/register-style titles

- [ ] **Step 5: Commit any concrete verification-driven rule fixes if needed**

```bash
git add config/sources/websites.yaml src/auto_report/pipeline/source_filters.py tests/test_sources.py
git commit -m "fix: tune edge source pack filters"
```

## Self-Review

### Spec coverage

- compact official edge / infra source pack: Task 2
- engineering-first source quality: Task 1 and Task 2
- stronger rejection of event / webinar / marketing noise: Task 1
- end-to-end verification against actual source balance: Task 3

No approved requirement from the source-pack design is left without a task.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later”
- Every task lists exact file paths
- Every code step contains concrete content
- Every verification step includes explicit commands and expected outcomes

### Type consistency

- `should_keep_candidate()` remains the central title/url filter used by `extract_listing_items()`
- new config ids match the ids asserted in tests
- the implementation stays within source config and filtering layers without changing AI pipeline interfaces
