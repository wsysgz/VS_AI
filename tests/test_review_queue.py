import json
from pathlib import Path

from auto_report.app import cmd_build_review_queue
from auto_report.pipeline.review_queue import build_review_issue_candidates


def _sample_payload() -> dict[str, object]:
    return {
        "signals": [
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "primary_domain": "ai-llm-agent",
                "score": 3.4,
                "lifecycle_state": "new",
                "risk_level": "high",
            },
            {
                "title": "Routine patch",
                "url": "https://example.com/patch",
                "primary_domain": "ai-llm-agent",
                "score": 1.2,
                "lifecycle_state": "verified",
                "risk_level": "low",
            },
        ],
        "analyses": [
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "vision vs evidence",
                "core_insight": "Interesting tool launch, but still needs outside corroboration.",
                "confidence": "low",
                "lifecycle_state": "new",
                "risk_level": "high",
                "enrichment": {"summary": "1 source(s) | community"},
                "support_evidence": [
                    {
                        "source_type": "paper",
                        "title": "Agent Debugger for Tool-Using Models",
                        "url": "https://arxiv.org/abs/2604.12345",
                        "evidence_scope": "external",
                    }
                ],
            },
            {
                "title": "Routine patch",
                "url": "https://example.com/patch",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "none",
                "core_insight": "Routine maintenance only.",
                "confidence": "high",
                "lifecycle_state": "verified",
                "risk_level": "low",
                "enrichment": {"summary": "2 source(s) | official / repo"},
                "support_evidence": [],
            },
        ],
    }


def test_build_review_issue_candidates_selects_high_value_topics_and_formats_issue_body():
    queue = build_review_issue_candidates(_sample_payload())

    assert len(queue) == 1
    issue = queue[0]
    assert issue["title"] == "[V7 review] Launch HN: Agent debugger"
    assert "Risk level: high" in issue["body"]
    assert "Lifecycle: new" in issue["body"]
    assert "Agent Debugger for Tool-Using Models" in issue["body"]
    assert "labels" in issue
    assert "review" in issue["labels"]
    assert "high-value" in issue["labels"]


def test_cmd_build_review_queue_writes_json_artifact(tmp_path: Path):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "latest-summary.json").write_text(
        json.dumps(_sample_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    output_path = cmd_build_review_queue(tmp_path)

    assert output_path == tmp_path / "out" / "review-queue" / "review-issues.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["issues"][0]["title"] == "[V7 review] Launch HN: Agent debugger"
