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


def test_extract_listing_items_reads_anchor_links():
    html = """
    <html><body>
      <a href="/post-a">AI 芯片发布</a>
      <a href="https://example.com/post-b">多模态边缘设备</a>
    </body></html>
    """

    items = extract_listing_items(
        source_id="semi-list",
        html=html,
        page_url="https://example.com/news",
        category_hint="ai-x-electronics",
    )

    assert len(items) == 2
    assert items[0].url == "https://example.com/post-a"
    assert items[1].title == "多模态边缘设备"
