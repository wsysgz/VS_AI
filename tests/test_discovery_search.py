import json
from pathlib import Path

from auto_report.pipeline.discovery_search import (
    build_discovery_search_artifact,
    load_keywords,
    parse_discovery_response,
)


def test_load_keywords_ignores_comments_and_blank_lines(tmp_path: Path):
    path = tmp_path / "keywords.txt"
    path.write_text(
        "# ai-llm-agent\nAnthropic news\n\n# ai-x-electronics\nJetson edge AI\n",
        encoding="utf-8",
    )

    keywords = load_keywords(path)

    assert keywords == ["Anthropic news", "Jetson edge AI"]


def test_parse_discovery_response_accepts_keyword_items_payload():
    payload = parse_discovery_response(
        json.dumps(
            {
                "summary": "Two promising candidates",
                "candidates": [
                    {
                        "title": "Anthropic News",
                        "url": "https://www.anthropic.com/news",
                        "classification": "official-site",
                        "confidence": "high",
                        "feed_candidate": "",
                        "rsshub_candidate": "",
                        "changedetection_candidate": "https://www.anthropic.com/news",
                        "next_action": "Create changedetection watch first",
                    }
                ],
            },
            ensure_ascii=False,
        )
    )

    assert payload["summary"] == "Two promising candidates"
    assert payload["candidates"][0]["classification"] == "official-site"
    assert payload["candidates"][0]["next_action"] == "Create changedetection watch first"


def test_build_discovery_search_artifact_writes_json_and_markdown(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "config" / "source_discovery"
    config_dir.mkdir(parents=True)
    keywords_path = config_dir / "keywords.txt"
    keywords_path.write_text("Anthropic news\nJetson edge AI\n", encoding="utf-8")

    responses = iter(
        [
            json.dumps(
                {
                    "summary": "Anthropic official news page is the best current anchor.",
                    "candidates": [
                        {
                            "title": "Anthropic News",
                            "url": "https://www.anthropic.com/news",
                            "classification": "official-site",
                            "confidence": "high",
                            "feed_candidate": "",
                            "rsshub_candidate": "",
                            "changedetection_candidate": "https://www.anthropic.com/news",
                            "next_action": "Use changedetection until feed is confirmed",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            json.dumps(
                {
                    "summary": "Jetson tag feed is a strong official source.",
                    "candidates": [
                        {
                            "title": "NVIDIA Jetson Blog Feed",
                            "url": "https://developer.nvidia.com/blog/tag/jetson/feed/",
                            "classification": "official-feed",
                            "confidence": "high",
                            "feed_candidate": "https://developer.nvidia.com/blog/tag/jetson/feed/",
                            "rsshub_candidate": "",
                            "changedetection_candidate": "",
                            "next_action": "Promote to rss source after validation",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        ]
    )

    monkeypatch.setattr(
        "auto_report.pipeline.discovery_search.call_llm",
        lambda prompt, stage=None: next(responses),
    )

    output_path = build_discovery_search_artifact(tmp_path, keywords_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    markdown_path = tmp_path / "out" / "discovery-search" / "discovery-search.md"

    assert output_path == tmp_path / "out" / "discovery-search" / "discovery-search.json"
    assert markdown_path.exists()
    assert payload["keyword_count"] == 2
    assert payload["items"][0]["keyword"] == "Anthropic news"
    assert payload["items"][1]["candidates"][0]["classification"] == "official-feed"
