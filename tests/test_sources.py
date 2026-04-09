from auto_report.pipeline.source_filters import should_keep_candidate
from auto_report.sources.github import normalize_github_repository_detail
from auto_report.sources.github import normalize_github_repositories
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import extract_listing_items


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
