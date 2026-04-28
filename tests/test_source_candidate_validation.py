import json
from pathlib import Path

from auto_report.pipeline.source_candidate_validation import validate_source_candidates


def test_validate_source_candidates_extracts_items_from_configured_source(tmp_path: Path, monkeypatch):
    sources_dir = tmp_path / "config" / "sources"
    sources_dir.mkdir(parents=True)
    (sources_dir / "websites.yaml").write_text(
        """
sources:
  - id: renesas-blog
    enabled: true
    mode: article_listing
    url: https://www.renesas.com/en/blogs
    category_hint: ai-x-electronics
    fetch_backend: curl
    link_selector: "a[href*='/en/blogs/']"
    include_url_patterns:
      - /en/blogs/
    include_title_patterns:
      - edge ai
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "auto_report.pipeline.source_candidate_validation.collector_module._fetch_source_body",
        lambda source: """
        <html><body>
          <a href="/en/blogs/edge-ai-quiet-intelligence-behind-everyday-industry">
            Edge AI: The Quiet Intelligence Behind Everyday Industry
          </a>
        </body></html>
        """,
    )

    output_path = validate_source_candidates(tmp_path, source_ids=["renesas-blog"])
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path == tmp_path / "out" / "source-governance" / "source-candidate-validation.json"
    assert payload["count"] == 1
    assert payload["items"][0]["source_id"] == "renesas-blog"
    assert payload["items"][0]["collector"]["status"] == "ok"
    assert payload["items"][0]["collector"]["item_count"] == 1
    assert payload["items"][0]["collector"]["sample_items"][0]["title"] == (
        "Edge AI: The Quiet Intelligence Behind Everyday Industry"
    )
    assert (tmp_path / "out" / "source-governance" / "source-candidate-validation.md").exists()


def test_validate_source_candidates_reads_urls_from_discovery_artifact(tmp_path: Path, monkeypatch):
    discovery_dir = tmp_path / "out" / "discovery-search"
    discovery_dir.mkdir(parents=True)
    discovery_path = discovery_dir / "discovery-search.json"
    discovery_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "keyword": "Renesas AI blog",
                        "candidates": [
                            {
                                "title": "Renesas blogs",
                                "url": "https://www.renesas.com/en/blogs",
                                "feed_candidate": "",
                                "changedetection_candidate": "https://www.renesas.com/en/blogs",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "auto_report.pipeline.source_candidate_validation._probe_url",
        lambda url, timeout_seconds=20: {
            "url": url,
            "requests": {"status": "failed", "error": "403"},
            "curl": {"status": "ok", "http_status": 200, "content_type": "text/html"},
        },
    )

    output_path = validate_source_candidates(tmp_path, input_path=discovery_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["count"] == 1
    assert payload["items"][0]["url"] == "https://www.renesas.com/en/blogs"
    assert payload["items"][0]["probe"]["curl"]["http_status"] == 200
