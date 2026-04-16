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
    assert registry["google-ai-edge"]["candidate_kind"] == "changedetection_watch"

    assert "st-blog" in rsshub_candidate_ids
    assert "google-ai-edge" in changedetection_ids
    assert "openvino-blog" in changedetection_ids
    assert "meta-ai-blog" in replacement_ids
    assert "ti-e2e-blog" in replacement_ids
