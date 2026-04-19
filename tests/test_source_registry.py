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

    assert governance["summary"]["manual_review_count"] >= 1
    assert governance["summary"]["rsshub_candidate_count"] >= 1
    assert governance["summary"]["changedetection_candidate_count"] >= 1
    assert governance["summary"]["replacement_candidate_count"] >= 1

    assert "nxp-edge-ai" in manual_review_ids
    assert "meta-ai-blog" not in manual_review_ids
    assert "st-blog" not in manual_review_ids
    assert "ti-e2e-blog" not in manual_review_ids

    assert registry["meta-ai-blog"]["candidate_kind"] == "none"
    assert registry["st-blog"]["candidate_kind"] == "none"
    assert registry["ti-e2e-blog"]["candidate_kind"] == "none"
    assert registry["anthropic-news"]["candidate_kind"] == "validated_listing"
    assert registry["nxp-edge-ai"]["candidate_kind"] == "manual_replace"
    assert registry["google-ai-edge"]["candidate_kind"] == "none"

    assert "st-blog" not in rsshub_candidate_ids
    assert "anthropic-news" not in changedetection_ids
    assert "meta-ai-blog" not in replacement_ids
    assert "ti-e2e-blog" not in replacement_ids
    assert "google-ai-edge" not in changedetection_ids
    assert "openvino-blog" not in changedetection_ids
    assert "nxp-edge-ai" in replacement_ids


def test_build_source_governance_queue_adds_operational_priority_views():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)
    governance = build_source_governance_queue(registry)

    assert "priority_queue" in governance
    assert "changedetection_watch_list" in governance

    priority_queue = governance["priority_queue"]
    changedetection_watch_list = governance["changedetection_watch_list"]

    assert priority_queue
    assert changedetection_watch_list
    assert priority_queue[0]["priority_score"] >= priority_queue[-1]["priority_score"]
    assert all("watch_target" in item for item in changedetection_watch_list)
    assert all(item["candidate_kind"] == "changedetection_watch" for item in changedetection_watch_list)
    assert all(item["watch_target"] == item["url"] for item in changedetection_watch_list)
    assert all(item["priority_label"] in {"high", "medium", "low"} for item in priority_queue)


def test_build_source_registry_treats_structured_pages_as_direct_official_polls():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)

    assert registry["meta-ai-blog"]["mode"] == "rss_feed"
    assert registry["meta-ai-blog"]["stability_tier"] == "stable-feed"
    assert registry["meta-ai-blog"]["watch_strategy"] == "feed-poll"
    assert registry["meta-ai-blog"]["replacement_target"] == "none"
    assert registry["meta-ai-blog"]["candidate_kind"] == "none"

    assert registry["st-blog"]["mode"] == "rss_feed"
    assert registry["st-blog"]["stability_tier"] == "stable-feed"
    assert registry["st-blog"]["watch_strategy"] == "feed-poll"
    assert registry["st-blog"]["replacement_target"] == "none"
    assert registry["st-blog"]["candidate_kind"] == "none"

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

    assert registry["openvino-blog"]["mode"] == "structured_page"
    assert registry["openvino-blog"]["stability_tier"] == "stable-page"
    assert registry["openvino-blog"]["watch_strategy"] == "page-poll"
    assert registry["openvino-blog"]["replacement_target"] == "none"
    assert registry["openvino-blog"]["candidate_kind"] == "none"

    assert registry["ti-e2e-blog"]["mode"] == "json_api"
    assert registry["ti-e2e-blog"]["stability_tier"] == "stable-api"
    assert registry["ti-e2e-blog"]["watch_strategy"] == "api-poll"
    assert registry["ti-e2e-blog"]["replacement_target"] == "none"
    assert registry["ti-e2e-blog"]["candidate_kind"] == "none"


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


def test_build_source_registry_marks_anthropic_news_as_validated_listing():
    settings = load_settings(Path.cwd())

    registry = build_source_registry(settings)

    assert registry["anthropic-news"]["collector"] == "websites"
    assert registry["anthropic-news"]["mode"] == "article_listing"
    assert registry["anthropic-news"]["stability_tier"] == "verified-listing"
    assert registry["anthropic-news"]["watch_strategy"] == "listing-poll"
    assert registry["anthropic-news"]["replacement_target"] == "none"
    assert registry["anthropic-news"]["candidate_kind"] == "validated_listing"
    assert registry["anthropic-news"]["candidate_value"] == "https://www.anthropic.com/news"
