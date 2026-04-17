from pathlib import Path

from auto_report.settings import load_settings
from auto_report.source_registry import build_source_governance_queue, build_source_registry


def test_build_source_governance_queue_groups_manual_review_and_rsshub_candidates():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)
    governance = build_source_governance_queue(registry)

    manual_review_ids = [item["source_id"] for item in governance["manual_review"]]
    rsshub_candidate_ids = [item["source_id"] for item in governance["rsshub_candidates"]]
    changedetection_ids = [item["source_id"] for item in governance["changedetection_candidates"]]
    replacement_ids = [item["source_id"] for item in governance["replacement_candidates"]]

    assert governance["summary"]["manual_review_count"] >= 4
    assert governance["summary"]["rsshub_candidate_count"] >= 1
    assert governance["summary"]["changedetection_candidate_count"] >= 1
    assert governance["summary"]["replacement_candidate_count"] >= 4

    assert "meta-ai-blog" in manual_review_ids
    assert "st-blog" in manual_review_ids
    assert "ti-e2e-blog" in manual_review_ids

    assert registry["meta-ai-blog"]["candidate_kind"] == "manual_replace"
    assert registry["st-blog"]["candidate_kind"] == "rsshub_route"
    assert registry["google-ai-edge"]["candidate_kind"] == "none"

    assert "st-blog" in rsshub_candidate_ids
    assert "openvino-blog" in changedetection_ids
    assert "meta-ai-blog" in replacement_ids
    assert "ti-e2e-blog" in replacement_ids
    assert "google-ai-edge" not in changedetection_ids


def test_build_source_registry_treats_structured_pages_as_direct_official_polls():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)

    assert registry["deepseek-updates"]["mode"] == "structured_page"
    assert registry["deepseek-updates"]["stability_tier"] == "stable-page"
    assert registry["deepseek-updates"]["watch_strategy"] == "page-poll"
    assert registry["deepseek-updates"]["replacement_target"] == "none"
    assert registry["deepseek-updates"]["candidate_kind"] == "none"

    assert registry["moonshot-blog"]["mode"] == "structured_page"
    assert registry["moonshot-blog"]["stability_tier"] == "stable-page"
    assert registry["moonshot-blog"]["watch_strategy"] == "page-poll"
    assert registry["moonshot-blog"]["replacement_target"] == "none"
    assert registry["moonshot-blog"]["candidate_kind"] == "none"


def test_build_source_registry_treats_json_api_sources_as_stable_official_polls():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)

    assert registry["qwen-blog"]["mode"] == "json_api"
    assert registry["qwen-blog"]["stability_tier"] == "stable-api"
    assert registry["qwen-blog"]["watch_strategy"] == "api-poll"
    assert registry["qwen-blog"]["replacement_target"] == "none"
    assert registry["qwen-blog"]["candidate_kind"] == "none"


def test_build_source_registry_treats_google_ai_edge_as_stable_rss_feed():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)

    assert registry["google-ai-edge"]["collector"] == "rss"
    assert registry["google-ai-edge"]["mode"] == "rss_feed"
    assert registry["google-ai-edge"]["stability_tier"] == "stable-feed"
    assert registry["google-ai-edge"]["watch_strategy"] == "feed-poll"
    assert registry["google-ai-edge"]["replacement_target"] == "none"
    assert registry["google-ai-edge"]["candidate_kind"] == "none"
