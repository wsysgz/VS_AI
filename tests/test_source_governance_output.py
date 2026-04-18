import json
import shutil
from pathlib import Path

from auto_report.outputs.source_governance import build_source_governance_artifact


def test_build_source_governance_artifact_writes_json(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    output_path = build_source_governance_artifact(tmp_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path == tmp_path / "out" / "source-governance" / "source-governance.json"
    assert "generated_at" in payload
    assert "source_registry" in payload
    assert "source_governance" in payload
    assert "changedetection_candidates" in payload["source_governance"]


def test_build_source_governance_artifact_includes_discovery_search_when_present(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    discovery_dir = tmp_path / "out" / "discovery-search"
    discovery_dir.mkdir(parents=True)
    (discovery_dir / "discovery-search.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T13:00:00+08:00",
                "provider": "minimax_svips",
                "model": "MiniMax-M2.7",
                "keywords_path": "config/source_discovery/keywords.txt",
                "keyword_count": 1,
                "items": [
                    {
                        "keyword": "Anthropic news",
                        "summary": "Discovery summary",
                        "candidates": [
                            {
                                "title": "Anthropic News",
                                "url": "https://www.anthropic.com/news",
                                "classification": "official-site",
                                "confidence": "high",
                                "feed_candidate": "",
                                "rsshub_candidate": "/anthropic/news",
                                "changedetection_candidate": "https://www.anthropic.com/news",
                                "next_action": "Review remotely",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = json.loads(build_source_governance_artifact(tmp_path).read_text(encoding="utf-8"))

    assert "discovery_search" in payload
    assert payload["discovery_search"]["keyword_count"] == 1
    assert payload["discovery_search"]["items"][0]["keyword"] == "Anthropic news"
    assert "official_feed_leads" in payload
    assert "rsshub_leads" in payload
    assert "changedetection_leads" in payload
    assert payload["rsshub_leads"][0]["keyword"] == "Anthropic news"
    assert payload["changedetection_leads"][0]["url"] == "https://www.anthropic.com/news"


def test_build_source_governance_artifact_builds_lead_views_from_discovery_candidates(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    discovery_dir = tmp_path / "out" / "discovery-search"
    discovery_dir.mkdir(parents=True)
    (discovery_dir / "discovery-search.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T13:00:00+08:00",
                "provider": "minimax_svips",
                "model": "MiniMax-M2.7",
                "keywords_path": "config/source_discovery/keywords.txt",
                "keyword_count": 1,
                "items": [
                    {
                        "keyword": "Jetson edge AI",
                        "summary": "Discovery summary",
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
                            },
                            {
                                "title": "NVIDIA Jetson RSSHub",
                                "url": "https://rsshub.app/nvidia/jetson",
                                "classification": "rsshub-candidate",
                                "confidence": "medium",
                                "feed_candidate": "",
                                "rsshub_candidate": "/nvidia/jetson",
                                "changedetection_candidate": "",
                                "next_action": "Validate RSSHub route",
                            },
                            {
                                "title": "Jetson Tag Page",
                                "url": "https://developer.nvidia.com/blog/tag/jetson/",
                                "classification": "changedetection-candidate",
                                "confidence": "medium",
                                "feed_candidate": "",
                                "rsshub_candidate": "",
                                "changedetection_candidate": "https://developer.nvidia.com/blog/tag/jetson/",
                                "next_action": "Use changedetection as fallback",
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = json.loads(build_source_governance_artifact(tmp_path).read_text(encoding="utf-8"))

    assert payload["official_feed_leads"][0]["feed_candidate"] == "https://developer.nvidia.com/blog/tag/jetson/feed/"
    assert payload["rsshub_leads"][0]["rsshub_candidate"] == "/nvidia/jetson"
    assert payload["changedetection_leads"][0]["changedetection_candidate"] == "https://developer.nvidia.com/blog/tag/jetson/"
