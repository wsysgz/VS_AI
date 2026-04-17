from concurrent.futures import TimeoutError
from pathlib import Path
import threading
import requests

from auto_report.models.records import CollectedItem
from auto_report.pipeline.source_filters import should_keep_candidate
from auto_report.settings import load_settings
from auto_report.sources import collector as collector_module
from auto_report.sources.collector import _fetch_text, collect_all_items
from auto_report.sources.github import normalize_github_repository_detail
from auto_report.sources.github import normalize_github_repositories
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import (
    extract_json_items,
    extract_listing_items,
    extract_structured_items,
)


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>Agent breakthrough</title>
      <link>https://example.com/agent-breakthrough</link>
      <description>Reasoning agent with multimodal support</description>
      <pubDate>Wed, 09 Apr 2026 08:00:00 GMT</pubDate>
      <category>agent</category>
      <category>multimodal</category>
    </item>
  </channel>
</rss>
"""


def test_parse_rss_content_returns_collected_items():
    items = parse_rss_content(
        source_id="sample-feed",
        content=RSS_SAMPLE,
        category_hint="ai-llm-agent",
    )

    assert len(items) == 1
    assert items[0].title == "Agent breakthrough"
    assert items[0].url == "https://example.com/agent-breakthrough"
    assert "agent" in items[0].tags


def test_parse_rss_content_respects_max_items():
    items = parse_rss_content(
        source_id="sample-feed",
        content=RSS_SAMPLE,
        category_hint="ai-llm-agent",
        max_items=1,
    )

    assert len(items) == 1


def test_parse_rss_content_respects_excluded_title_patterns():
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Sample Feed</title>
        <item>
          <title>OpenAI Full Fan Mode Contest: Terms &amp; Conditions</title>
          <link>https://example.com/contest</link>
          <description>Low-signal legal post</description>
        </item>
        <item>
          <title>The next phase of enterprise AI</title>
          <link>https://example.com/enterprise-ai</link>
          <description>High-signal product and adoption update</description>
        </item>
      </channel>
    </rss>
    """

    items = parse_rss_content(
        source_id="sample-feed",
        content=content,
        category_hint="ai-llm-agent",
        source_rules={
            "exclude_title_patterns": ["contest", "terms & conditions"],
        },
    )

    assert [item.title for item in items] == ["The next phase of enterprise AI"]


def test_parse_rss_content_respects_included_title_patterns():
    content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Sample Feed</title>
        <item>
          <title>A new way to explore the web with AI Mode in Chrome</title>
          <link>https://example.com/chrome-ai-mode</link>
          <description>Broad consumer AI update</description>
        </item>
        <item>
          <title>On-device GenAI in Chrome, Chromebook Plus, and Pixel Watch with LiteRT</title>
          <link>https://example.com/litert-on-device</link>
          <description>Edge AI update with LiteRT</description>
        </item>
      </channel>
    </rss>
    """

    items = parse_rss_content(
        source_id="sample-feed",
        content=content,
        category_hint="ai-x-electronics",
        source_rules={
            "include_title_patterns": ["litert", "on-device", "edge ai", "npu"],
        },
    )

    assert [item.title for item in items] == [
        "On-device GenAI in Chrome, Chromebook Plus, and Pixel Watch with LiteRT"
    ]


def test_normalize_github_repositories_maps_repo_payload():
    payload = {
        "items": [
            {
                "full_name": "example/agent",
                "html_url": "https://github.com/example/agent",
                "description": "Agent toolkit",
                "topics": ["agent", "llm"],
                "language": "Python",
                "stargazers_count": 1200,
                "updated_at": "2026-04-09T08:00:00Z",
            }
        ]
    }

    items = normalize_github_repositories(
        source_id="github-ai-search",
        payload=payload,
        category_hint="ai-llm-agent",
    )

    assert len(items) == 1
    assert items[0].title == "example/agent"
    assert items[0].metadata["stars"] == 1200
    assert "llm" in items[0].tags


def test_normalize_github_repository_detail_maps_single_repository():
    item = normalize_github_repository_detail(
        source_id="curated-agent-repos",
        payload={
            "full_name": "langchain-ai/langgraph",
            "html_url": "https://github.com/langchain-ai/langgraph",
            "description": "Agent orchestration library",
            "topics": ["agent", "workflow"],
            "language": "Python",
            "stargazers_count": 9999,
            "updated_at": "2026-04-10T00:00:00Z",
        },
        category_hint="ai-llm-agent",
    )

    assert item is not None
    assert item.title == "langchain-ai/langgraph"
    assert item.metadata["stars"] == 9999


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

    items = extract_listing_items(
        {
            "id": "anthropic-news",
            "url": "https://example.com/news",
            "category_hint": "ai-llm-agent",
            "link_selector": "a",
            "include_url_patterns": ["/news/"],
            "exclude_url_patterns": ["/about", "#"],
        },
        html,
    )

    assert len(items) == 1
    assert items[0].title == "Anthropic launches release A"
    assert items[0].url == "https://example.com/news/release-a"


def test_extract_listing_items_prefers_heading_text_and_strips_card_noise():
    html = """
    <html><body>
      <a href="/news/release-a">
        <div>Product</div>
        <time>Feb 17, 2026</time>
        <h4>Introducing Claude Sonnet 4.6</h4>
        <p>Frontier performance across coding and agent work.</p>
      </a>
      <a href="/news/release-b">
        <div>Apr 6, 2026</div>
        <div>Announcements</div>
        <span>Anthropic expands partnership with Google and Broadcom</span>
      </a>
    </body></html>
    """

    items = extract_listing_items(
        {
            "id": "anthropic-news",
            "url": "https://www.anthropic.com/news",
            "category_hint": "ai-llm-agent",
            "link_selector": "a[href^='/news/']",
            "include_url_patterns": ["/news/"],
            "exclude_url_patterns": ["/about", "#"],
        },
        html,
    )

    assert [item.title for item in items] == [
        "Introducing Claude Sonnet 4.6",
        "Anthropic expands partnership with Google and Broadcom",
    ]


def test_should_keep_candidate_drops_webinar_and_event_noise_by_default():
    source = {
        "include_url_patterns": ["/blog/", "/edge/", "/embedded/"],
    }

    assert should_keep_candidate(
        "Jetson embedded edge inference update",
        "https://developer.nvidia.com/blog/jetson-embedded-edge-inference",
        source,
    ) is True
    assert should_keep_candidate(
        "Register for our Edge AI Webinar",
        "https://example.com/blog/edge-ai-guide",
        source,
    ) is False
    assert should_keep_candidate(
        "OpenVINO event for developers",
        "https://example.com/blog/openvino-runtime-update",
        source,
    ) is False


def test_extract_listing_items_drops_white_paper_and_webinar_cards():
    html = """
    <html><body>
      <a href="/blog/jetson-edge-ai">
        <h3>Jetson edge AI pipeline update</h3>
      </a>
      <a href="/blog/edge-ai-webinar">
        <h3>Edge AI webinar for developers</h3>
      </a>
      <a href="/blog/openvino-white-paper">
        <h3>OpenVINO white paper for AI PCs</h3>
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
            "include_title_patterns": ["jetson", "edge", "embedded", "openvino"],
        },
        html,
    )

    assert [item.title for item in items] == ["Jetson edge AI pipeline update"]


def test_extract_structured_items_reads_entry_title_link_and_date():
    html = """
    <html><body>
      <article class="update-entry">
        <h2><a href="/updates/v3-2">DeepSeek-V3.2</a></h2>
        <time datetime="2025-12-01">2025-12-01</time>
      </article>
      <article class="update-entry">
        <h2><a href="/updates/v3-1">DeepSeek-V3.1</a></h2>
        <time datetime="2025-08-21">2025-08-21</time>
      </article>
    </body></html>
    """

    items = extract_structured_items(
        {
            "id": "deepseek-updates",
            "url": "https://api-docs.deepseek.com/updates/",
            "category_hint": "ai-llm-agent",
            "entry_selector": "article.update-entry",
            "title_selector": "h2",
            "link_selector": "h2 a[href]",
            "date_selector": "time",
            "include_url_patterns": ["/updates/"],
        },
        html,
    )

    assert [item.title for item in items] == ["DeepSeek-V3.2", "DeepSeek-V3.1"]
    assert [item.url for item in items] == [
        "https://api-docs.deepseek.com/updates/v3-2",
        "https://api-docs.deepseek.com/updates/v3-1",
    ]
    assert items[0].published_at == "2025-12-01"


def test_extract_json_items_reads_articles_from_official_api_payload():
    payload = {
        "success": True,
        "data": {
            "articles": [
                {
                    "title": "Qwen3.6-35B-A3B：智能体编程利器，现已开源",
                    "path": "qwen3.6-35b-a3b",
                    "extra": {"date": "2026/04/15"},
                },
                {
                    "title": "Qwen3.6-Plus：走向现实世界智能体",
                    "path": "qwen3.6-plus",
                    "extra": {"date": "2026/04/02"},
                },
            ]
        },
    }

    items = extract_json_items(
        {
            "id": "qwen-blog",
            "url": "https://qwen.ai/research#research_latest_advancements",
            "category_hint": "ai-llm-agent",
            "json_items_path": ["data", "articles"],
            "item_title_field": "title",
            "item_link_field": "path",
            "item_link_template": "https://qwen.ai/blog?id={value}",
            "item_date_field": "extra.date",
        },
        payload,
    )

    assert [item.title for item in items] == [
        "Qwen3.6-35B-A3B：智能体编程利器，现已开源",
        "Qwen3.6-Plus：走向现实世界智能体",
    ]
    assert [item.url for item in items] == [
        "https://qwen.ai/blog?id=qwen3.6-35b-a3b",
        "https://qwen.ai/blog?id=qwen3.6-plus",
    ]
    assert items[0].published_at == "2026/04/15"


def test_collect_websites_aggregates_enabled_sites(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["websites"] = {
        "sources": [
            {"id": "site-a", "url": "https://example.com/a", "enabled": True, "max_items": 2},
            {"id": "site-b", "url": "https://example.com/b", "enabled": True, "max_items": 2},
            {"id": "site-c", "url": "https://example.com/c", "enabled": False, "max_items": 2},
        ]
    }

    barrier = threading.Barrier(2)
    lock = threading.Lock()
    active_calls = 0
    max_active_calls = 0

    def fake_fetch(url: str, timeout: int = 20) -> str:
        nonlocal active_calls, max_active_calls
        with lock:
            active_calls += 1
            max_active_calls = max(max_active_calls, active_calls)
        try:
            barrier.wait(timeout=0.1)
        except threading.BrokenBarrierError:
            pass
        finally:
            with lock:
                active_calls -= 1
        return f"<html>{url}</html>"

    def fake_extract(source: dict, html: str) -> list[CollectedItem]:
        return [
            CollectedItem(
                source_id=str(source["id"]),
                item_id=str(source["id"]),
                title=f'{source["id"]}-headline',
                url=str(source["url"]),
                summary=html,
                published_at="2026-04-09T08:00:00+00:00",
                collected_at="2026-04-09T08:05:00+00:00",
                tags=["site"],
                language="en",
                metadata={},
            )
        ]

    monkeypatch.setattr("auto_report.sources.collector._fetch_text", fake_fetch)
    monkeypatch.setattr("auto_report.sources.collector.extract_listing_items", fake_extract)

    items, diagnostics = collector_module._collect_websites(settings)

    assert [item.title for item in items] == ["site-a-headline", "site-b-headline"]
    assert diagnostics == []
    assert max_active_calls == 2


def test_collect_websites_dispatches_structured_sources(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["websites"] = {
        "sources": [
            {"id": "site-a", "url": "https://example.com/a", "enabled": True, "mode": "structured_page"},
            {"id": "site-b", "url": "https://example.com/b", "enabled": True},
        ]
    }

    def fake_fetch(url: str, timeout: int = 20) -> str:
        return f"<html>{url}</html>"

    def fake_structured(source: dict, html: str) -> list[CollectedItem]:
        return [
            CollectedItem(
                source_id=str(source["id"]),
                item_id=f'{source["id"]}:structured',
                title=f'{source["id"]}-structured',
                url=str(source["url"]),
                summary=html,
                published_at="2026-04-09T08:00:00+00:00",
                collected_at="2026-04-09T08:05:00+00:00",
                tags=["site"],
                language="en",
                metadata={},
            )
        ]

    def fake_listing(source: dict, html: str) -> list[CollectedItem]:
        return [
            CollectedItem(
                source_id=str(source["id"]),
                item_id=f'{source["id"]}:listing',
                title=f'{source["id"]}-listing',
                url=str(source["url"]),
                summary=html,
                published_at="2026-04-09T08:00:00+00:00",
                collected_at="2026-04-09T08:05:00+00:00",
                tags=["site"],
                language="en",
                metadata={},
            )
        ]

    monkeypatch.setattr("auto_report.sources.collector._fetch_text", fake_fetch)
    monkeypatch.setattr("auto_report.sources.collector.extract_structured_items", fake_structured)
    monkeypatch.setattr("auto_report.sources.collector.extract_listing_items", fake_listing)

    items, diagnostics = collector_module._collect_websites(settings)

    assert [item.title for item in items] == ["site-a-structured", "site-b-listing"]
    assert diagnostics == []


def test_collect_websites_dispatches_json_api_sources(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["websites"] = {
        "sources": [
            {
                "id": "site-a",
                "url": "https://example.com/a",
                "api_url": "https://example.com/api/a",
                "enabled": True,
                "mode": "json_api",
            },
        ]
    }

    def fake_fetch(url: str, timeout: int = 20, retries: int = 1) -> str:
        assert url == "https://example.com/api/a"
        return '{"data": {"articles": []}}'

    def fake_extract(source: dict, payload: dict) -> list[CollectedItem]:
        return [
            CollectedItem(
                source_id=str(source["id"]),
                item_id=f'{source["id"]}:json',
                title=f'{source["id"]}-json',
                url="https://example.com/item",
                summary="",
                published_at="2026-04-09T08:00:00+00:00",
                collected_at="2026-04-09T08:05:00+00:00",
                tags=["site"],
                language="en",
                metadata={},
            )
        ]

    monkeypatch.setattr("auto_report.sources.collector._fetch_text", fake_fetch)
    monkeypatch.setattr("auto_report.sources.collector.extract_json_items", fake_extract)

    items, diagnostics = collector_module._collect_websites(settings)

    assert [item.title for item in items] == ["site-a-json"]
    assert diagnostics == []


def test_collect_websites_keeps_other_results_when_one_site_fails(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["websites"] = {
        "sources": [
            {"id": "site-a", "url": "https://example.com/a", "enabled": True, "max_items": 2},
            {"id": "site-b", "url": "https://example.com/b", "enabled": True, "max_items": 2},
        ]
    }

    def fake_fetch(url: str, timeout: int = 20) -> str:
        if url.endswith("/b"):
            raise RuntimeError("boom")
        return f"<html>{url}</html>"

    def fake_extract(source: dict, html: str) -> list[CollectedItem]:
        return [
            CollectedItem(
                source_id=str(source["id"]),
                item_id=str(source["id"]),
                title=f'{source["id"]}-headline',
                url=str(source["url"]),
                summary=html,
                published_at="2026-04-09T08:00:00+00:00",
                collected_at="2026-04-09T08:05:00+00:00",
                tags=["site"],
                language="en",
                metadata={},
            )
        ]

    monkeypatch.setattr("auto_report.sources.collector._fetch_text", fake_fetch)
    monkeypatch.setattr("auto_report.sources.collector.extract_listing_items", fake_extract)

    items, diagnostics = collector_module._collect_websites(settings)

    assert [item.title for item in items] == ["site-a-headline"]
    assert diagnostics == ["Website source failed: site-b -> boom"]


def test_collect_websites_records_timeout_errors_as_diagnostics(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["websites"] = {
        "sources": [
            {"id": "site-a", "url": "https://example.com/a", "enabled": True, "max_items": 2},
        ]
    }

    monkeypatch.setattr(
        "auto_report.sources.collector._fetch_text",
        lambda url, timeout=20: (_ for _ in ()).throw(TimeoutError("slow site")),
    )

    items, diagnostics = collector_module._collect_websites(settings)

    assert items == []
    assert diagnostics == ["Website source failed: site-a -> slow site"]


def test_fetch_text_retries_once_on_connection_reset(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        text = "<html>ok</html>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, timeout: int = 20, headers: dict | None = None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.ConnectionError("connection reset")
        return DummyResponse()

    monkeypatch.setattr("auto_report.sources.collector.requests.get", fake_get)

    result = _fetch_text("https://example.com")

    assert result == "<html>ok</html>"
    assert calls["count"] == 2


def test_fetch_text_does_not_retry_http_errors(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        text = ""

        def raise_for_status(self) -> None:
            raise requests.HTTPError("404 not found")

    def fake_get(url: str, timeout: int = 20, headers: dict | None = None):
        calls["count"] += 1
        return DummyResponse()

    monkeypatch.setattr("auto_report.sources.collector.requests.get", fake_get)

    try:
        _fetch_text("https://example.com")
    except requests.HTTPError as exc:
        assert "404 not found" in str(exc)
    else:
        raise AssertionError("expected HTTPError")

    assert calls["count"] == 1


def test_collect_all_items_records_timeout_as_diagnostic(monkeypatch):
    settings = load_settings(Path.cwd())
    sample_item = CollectedItem(
        source_id="rss",
        item_id="1",
        title="Agent breakthrough",
        url="https://example.com/agent-breakthrough",
        summary="Reasoning agent with multimodal support",
        published_at="2026-04-09T08:00:00+00:00",
        collected_at="2026-04-09T08:05:00+00:00",
        tags=["agent"],
        language="en",
        metadata={},
    )

    monkeypatch.setattr("auto_report.sources.collector._collect_rss", lambda settings: ([sample_item], ["rss ok"]))
    monkeypatch.setattr("auto_report.sources.collector._collect_github", lambda settings: ([], ["github ok"]))
    monkeypatch.setattr("auto_report.sources.collector._collect_websites", lambda settings: ([], ["web ok"]))
    monkeypatch.setattr("auto_report.sources.collector._collect_hn", lambda settings: ([], ["hn ok"]))

    def fake_as_completed(futures, timeout=None):
        futures = list(futures)
        yield futures[0]
        raise TimeoutError("1 (of 4) futures unfinished")

    monkeypatch.setattr("auto_report.sources.collector.as_completed", fake_as_completed)

    items, diagnostics = collect_all_items(settings)

    assert [item.title for item in items] == ["Agent breakthrough"]
    assert any("timed out" in message for message in diagnostics)


def test_collect_rss_uses_source_specific_timeout(monkeypatch):
    settings = load_settings(Path.cwd())
    settings.sources["rss"] = {
        "sources": [
            {
                "id": "youtube-google-developers",
                "enabled": True,
                "url": "https://www.youtube.com/feeds/videos.xml?user=GoogleDevelopers",
                "category_hint": "ai-x-electronics",
                "max_items": 2,
                "timeout_seconds": 8,
            }
        ]
    }

    seen: list[int] = []

    def fake_fetch(url: str, timeout: int = 20, retries: int = 1) -> str:
        seen.append(timeout)
        return RSS_SAMPLE

    monkeypatch.setattr("auto_report.sources.collector._fetch_text", fake_fetch)

    items, diagnostics = collector_module._collect_rss(settings)

    assert [item.title for item in items] == ["Agent breakthrough"]
    assert diagnostics == []
    assert seen == [8]
