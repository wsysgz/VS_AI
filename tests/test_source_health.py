from pathlib import Path

from auto_report.app import _summarize_source_health
from auto_report.settings import load_settings


def test_summarize_source_health_includes_per_source_breakdown():
    settings = load_settings(Path.cwd())

    summary = _summarize_source_health(
        settings,
        [
            "RSS source failed: meta-ai-blog -> 404 Client Error: Not Found",
            "Website source failed: google-ai-edge -> Read timed out",
            "Website collectors timed out: openvino-blog, qwen-blog",
            "GitHub repo failed: NVIDIA/TensorRT -> 404 Client Error: Not Found",
            "HN source failed: timed out",
        ],
    )

    sources = summary["sources"]

    assert sources["meta-ai-blog"]["collector"] == "rss"
    assert sources["meta-ai-blog"]["failure_count"] == 1
    assert "not_found" in sources["meta-ai-blog"]["error_categories"]

    assert sources["google-ai-edge"]["collector"] == "websites"
    assert sources["google-ai-edge"]["failure_count"] == 1
    assert "timeout" in sources["google-ai-edge"]["error_categories"]

    assert sources["openvino-blog"]["collector"] == "websites"
    assert sources["openvino-blog"]["failure_count"] == 1
    assert sources["qwen-blog"]["failure_count"] == 1

    assert sources["NVIDIA/TensorRT"]["collector"] == "github"
    assert sources["NVIDIA/TensorRT"]["source_group"] == "curated-chip-ai-repos"

    assert sources["hacker_news"]["collector"] == "hacker_news"
    assert sources["hacker_news"]["failure_count"] == 1

