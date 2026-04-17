from pathlib import Path

from auto_report.app import _summarize_source_health
from auto_report.settings import load_settings


def test_summarize_source_health_includes_per_source_breakdown():
    settings = load_settings(Path.cwd())

    summary = _summarize_source_health(
        settings,
        [
            "RSS source failed: meta-ai-blog -> 404 Client Error: Not Found",
            "RSS source failed: google-ai-edge -> Read timed out",
            "Website collectors timed out: openvino-blog, qwen-blog",
            "GitHub repo failed: NVIDIA/TensorRT -> 404 Client Error: Not Found",
            "HN source failed: timed out",
        ],
    )

    sources = summary["sources"]

    assert sources["meta-ai-blog"]["collector"] == "rss"
    assert sources["meta-ai-blog"]["failure_count"] == 1
    assert "not_found" in sources["meta-ai-blog"]["error_categories"]
    assert sources["meta-ai-blog"]["stability_tier"] == "stable-feed"
    assert sources["meta-ai-blog"]["replacement_hint"] == ""
    assert sources["meta-ai-blog"]["watch_strategy"] == "feed-poll"
    assert sources["meta-ai-blog"]["replacement_target"] == "none"
    assert sources["meta-ai-blog"]["candidate_kind"] == "none"

    assert sources["google-ai-edge"]["collector"] == "rss"
    assert sources["google-ai-edge"]["failure_count"] == 1
    assert "timeout" in sources["google-ai-edge"]["error_categories"]
    assert sources["google-ai-edge"]["stability_tier"] == "stable-feed"
    assert sources["google-ai-edge"]["replacement_hint"] == ""
    assert sources["google-ai-edge"]["watch_strategy"] == "feed-poll"
    assert sources["google-ai-edge"]["replacement_target"] == "none"
    assert sources["google-ai-edge"]["candidate_kind"] == "none"
    assert sources["google-ai-edge"]["candidate_value"] == ""

    assert sources["openvino-blog"]["collector"] == "websites"
    assert sources["openvino-blog"]["failure_count"] == 1
    assert sources["openvino-blog"]["stability_tier"] == "stable-page"
    assert sources["openvino-blog"]["watch_strategy"] == "page-poll"
    assert sources["openvino-blog"]["replacement_target"] == "none"
    assert sources["openvino-blog"]["candidate_kind"] == "none"
    assert sources["qwen-blog"]["failure_count"] == 1

    assert sources["NVIDIA/TensorRT"]["collector"] == "github"
    assert sources["NVIDIA/TensorRT"]["source_group"] == "curated-chip-ai-repos"
    assert sources["NVIDIA/TensorRT"]["stability_tier"] == "stable-feed"
    assert sources["NVIDIA/TensorRT"]["watch_strategy"] == "repo-poll"
    assert sources["NVIDIA/TensorRT"]["candidate_kind"] == "none"

    assert sources["hacker_news"]["collector"] == "hacker_news"
    assert sources["hacker_news"]["failure_count"] == 1
    assert sources["hacker_news"]["stability_tier"] == "dynamic-site"
    assert sources["hacker_news"]["watch_strategy"] == "opportunistic-poll"
    assert sources["hacker_news"]["replacement_target"] == "none"


def test_summarize_source_health_ignores_non_failure_diagnostics():
    settings = load_settings(Path.cwd())

    summary = _summarize_source_health(
        settings,
        [
            "HN: fetched 59 raw, filtered to 16 relevant (min_score=10)",
            "collect_all_items completed successfully",
            "RSS source failed: meta-ai-blog -> 404 Client Error: Not Found",
        ],
    )

    assert summary["total"] == 1
    assert summary["not_found"] == 1
    assert summary["other"] == 0
    assert summary["samples"] == ["RSS source failed: meta-ai-blog -> 404 Client Error: Not Found"]
    assert list(summary["sources"]) == ["meta-ai-blog"]

