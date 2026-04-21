import json
import shutil
from pathlib import Path

import yaml

from auto_report.pipeline.source_updates import apply_source_updates


def _read_sources(path: Path) -> list[dict[str, object]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload.get("sources", [])


def test_apply_source_updates_moves_feed_upgrades_and_updates_local_governance(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    review_queue_dir = tmp_path / "out" / "review-queue"
    review_queue_dir.mkdir(parents=True)
    (review_queue_dir / "candidate-updates.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T10:00:00+08:00",
                "count": 4,
                "updates": [
                    {
                        "lead_key": "official_feed_leads|Qualcomm|Feed|https://www.qualcomm.com/news/onq",
                        "source_id": "qualcomm-onq",
                        "target_kind": "official_feed",
                        "candidate_value": "https://www.qualcomm.com/news/onq/feed",
                        "target_file": "config/sources/rss.yaml",
                        "suggested_fields": {
                            "id": "qualcomm-onq",
                            "collector": "rss",
                            "enabled": True,
                            "mode": "rss_feed",
                            "url": "https://www.qualcomm.com/news/onq/feed",
                            "category_hint": "ai-x-electronics",
                        },
                        "apply_ready": True,
                        "blocking_reason": "",
                        "priority_score": 100,
                    },
                    {
                        "lead_key": "changedetection_leads|Infineon|Watch|https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                        "source_id": "infineon-blog",
                        "target_kind": "changedetection",
                        "candidate_value": "https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                        "target_file": "config/sources/websites.yaml",
                        "suggested_fields": {
                            "id": "infineon-blog",
                            "collector": "websites",
                            "enabled": True,
                            "mode": "article_listing",
                            "url": "https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                            "candidate_kind": "changedetection_watch",
                            "candidate_value": "https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                            "watch_strategy": "changedetection-watch",
                            "next_action": "Create a changedetection watch for this URL and store the watch reference.",
                        },
                        "apply_ready": True,
                        "blocking_reason": "",
                        "priority_score": 90,
                    },
                    {
                        "lead_key": "official_feed_leads|Anthropic|Listing|https://www.anthropic.com/news",
                        "source_id": "anthropic-news",
                        "target_kind": "validated_listing",
                        "candidate_value": "https://www.anthropic.com/news",
                        "target_file": "config/sources/websites.yaml",
                        "suggested_fields": {
                            "id": "anthropic-news",
                            "collector": "websites",
                            "enabled": True,
                            "mode": "article_listing",
                            "url": "https://www.anthropic.com/news",
                            "category_hint": "ai-llm-agent",
                            "stability_tier": "verified-listing",
                            "watch_strategy": "listing-poll",
                            "replacement_target": "none",
                            "candidate_kind": "validated_listing",
                            "candidate_value": "https://www.anthropic.com/news",
                        },
                        "apply_ready": True,
                        "blocking_reason": "",
                        "priority_score": 80,
                    },
                    {
                        "lead_key": "official_feed_leads|Unknown|Blocked|https://example.com/unknown",
                        "source_id": "",
                        "target_kind": "official_feed",
                        "candidate_value": "https://example.com/feed.xml",
                        "target_file": "config/sources/rss.yaml",
                        "suggested_fields": {
                            "id": "",
                            "collector": "rss",
                            "enabled": True,
                            "mode": "rss_feed",
                            "url": "https://example.com/feed.xml",
                        },
                        "apply_ready": False,
                        "blocking_reason": "Needs manual source mapping",
                        "priority_score": 10,
                    },
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = apply_source_updates(tmp_path, dry_run=False)

    rss_sources = {item["id"]: item for item in _read_sources(tmp_path / "config" / "sources" / "rss.yaml")}
    website_sources = {item["id"]: item for item in _read_sources(tmp_path / "config" / "sources" / "websites.yaml")}

    assert result["applied_count"] == 3
    assert result["skipped_count"] == 1
    assert "qualcomm-onq" in rss_sources
    assert rss_sources["qualcomm-onq"]["url"] == "https://www.qualcomm.com/news/onq/feed"
    assert "qualcomm-onq" not in website_sources
    assert website_sources["anthropic-news"]["candidate_kind"] == "validated_listing"
    assert website_sources["infineon-blog"]["watch_strategy"] == "changedetection-watch"
    assert website_sources["infineon-blog"]["candidate_kind"] == "changedetection_watch"
    assert (tmp_path / "out" / "review-queue" / "applied-source-updates.json").exists()


def test_apply_source_updates_dry_run_does_not_modify_configs(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    review_queue_dir = tmp_path / "out" / "review-queue"
    review_queue_dir.mkdir(parents=True)
    (review_queue_dir / "candidate-updates.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T10:00:00+08:00",
                "count": 1,
                "updates": [
                    {
                        "lead_key": "official_feed_leads|Qualcomm|Feed|https://www.qualcomm.com/news/onq",
                        "source_id": "qualcomm-onq",
                        "target_kind": "official_feed",
                        "candidate_value": "https://www.qualcomm.com/news/onq/feed",
                        "target_file": "config/sources/rss.yaml",
                        "suggested_fields": {
                            "id": "qualcomm-onq",
                            "collector": "rss",
                            "enabled": True,
                            "mode": "rss_feed",
                            "url": "https://www.qualcomm.com/news/onq/feed",
                            "category_hint": "ai-x-electronics",
                        },
                        "apply_ready": True,
                        "blocking_reason": "",
                        "priority_score": 100,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    before_rss = (tmp_path / "config" / "sources" / "rss.yaml").read_text(encoding="utf-8")
    before_websites = (tmp_path / "config" / "sources" / "websites.yaml").read_text(encoding="utf-8")

    result = apply_source_updates(tmp_path, dry_run=True)

    assert result["applied_count"] == 1
    assert result["dry_run"] is True
    assert (tmp_path / "config" / "sources" / "rss.yaml").read_text(encoding="utf-8") == before_rss
    assert (tmp_path / "config" / "sources" / "websites.yaml").read_text(encoding="utf-8") == before_websites


def test_apply_source_updates_promotes_watch_updates_into_registry(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "changedetection-watch-registry.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T10:00:00+08:00",
                "count": 1,
                "summary": {"status_counts": {"planned": 1}},
                "items": [
                    {
                        "source_id": "infineon-blog",
                        "watch_target": "https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                        "priority_score": 90,
                        "priority_label": "high",
                        "status": "planned",
                        "note": "",
                        "watch_url": "",
                        "watch_reference": "",
                        "next_action": "Create a changedetection watch for this URL and store the watch reference.",
                        "updated_at": "",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    review_queue_dir = tmp_path / "out" / "review-queue"
    review_queue_dir.mkdir(parents=True, exist_ok=True)
    (review_queue_dir / "candidate-updates.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T10:00:00+08:00",
                "count": 1,
                "updates": [
                    {
                        "update_kind": "watch_update",
                        "source_id": "infineon-blog",
                        "target_kind": "changedetection_watch",
                        "candidate_value": "https://www.infineon.com/cms/en/about-infineon/press/press-releases/",
                        "target_file": "out/source-governance/changedetection-watch-registry.json",
                        "suggested_fields": {"status": "active_local"},
                        "apply_ready": True,
                        "blocking_reason": "",
                        "priority_score": 90,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = apply_source_updates(tmp_path, dry_run=False)
    registry_payload = json.loads((governance_dir / "changedetection-watch-registry.json").read_text(encoding="utf-8"))
    infineon = next(item for item in registry_payload["items"] if item["source_id"] == "infineon-blog")

    assert result["applied_count"] == 1
    assert result["applied_watch_count"] == 1
    assert any(path.endswith("changedetection-watch-registry.json") for path in result["modified_files"])
    assert infineon["status"] == "active_local"
    assert infineon["updated_at"]
