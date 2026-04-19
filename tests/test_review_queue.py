import json
from pathlib import Path

from auto_report.app import cmd_build_review_queue
from auto_report.pipeline.review_queue import (
    build_review_issue_candidates,
    build_approved_source_lead_updates,
    build_source_lead_review_candidates,
)


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


def _sample_governance_payload() -> dict[str, object]:
    return {
        "source_registry": {
            "anthropic-news": {
                "url": "https://www.anthropic.com/news",
            }
        },
        "source_governance": {
            "priority_queue": [
                {
                    "source_id": "anthropic-news",
                    "url": "https://www.anthropic.com/news",
                }
            ]
        },
        "official_feed_leads": [
            {
                "keyword": "Anthropic news",
                "title": "Anthropic 官方博客",
                "url": "https://www.anthropic.com/news",
                "classification": "official-site",
                "confidence": "high",
                "feed_candidate": "https://www.anthropic.com/news/feed",
                "rsshub_candidate": "/anthropic/news",
                "changedetection_candidate": "https://www.anthropic.com/news",
                "next_action": "优先验证官方 feed。",
            }
        ],
        "rsshub_leads": [
            {
                "keyword": "OpenAI safety updates",
                "title": "RSSHub candidate",
                "url": "https://openai.com/blog/tag/safety",
                "classification": "rsshub-candidate",
                "confidence": "medium",
                "feed_candidate": "",
                "rsshub_candidate": "/openai/blog/tag/safety",
                "changedetection_candidate": "",
                "next_action": "检查 RSSHub 路由是否可用。",
            }
        ],
        "changedetection_leads": [
            {
                "keyword": "Jetson edge AI",
                "title": "NVIDIA Jetson blog",
                "url": "https://developer.nvidia.com/blog/tag/jetson/",
                "classification": "official-site",
                "confidence": "high",
                "feed_candidate": "",
                "rsshub_candidate": "",
                "changedetection_candidate": "https://developer.nvidia.com/blog/tag/jetson/",
                "next_action": "建立 changedetection watch。",
            }
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


def test_build_source_lead_review_candidates_formats_governance_leads():
    queue = build_source_lead_review_candidates(_sample_governance_payload(), limit_per_kind=2)

    assert len(queue) == 3
    first = queue[0]
    assert first["meta"]["source_id"] == "anthropic-news"
    assert first["title"].startswith("[Lead review]")
    assert "Keyword: Anthropic news" in first["body"]
    assert "Next action: 优先验证官方 feed。" in first["body"]
    assert "source-governance" in first["labels"]
    assert any(label.startswith("lead-") for label in first["labels"])
    assert first["meta"]["priority_score"] >= queue[-1]["meta"]["priority_score"]


def test_cmd_build_review_queue_writes_clustered_lead_payload_and_status_file(tmp_path: Path):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "latest-summary.json").write_text(
        json.dumps(_sample_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "source-governance.json").write_text(
        json.dumps(_sample_governance_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    output_path = cmd_build_review_queue(tmp_path)

    assert output_path == tmp_path / "out" / "review-queue" / "review-issues.json"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["issues"][0]["title"] == "[V7 review] Launch HN: Agent debugger"
    lead_path = tmp_path / "out" / "review-queue" / "source-lead-issues.json"
    lead_payload = json.loads(lead_path.read_text(encoding="utf-8"))
    assert lead_payload["count"] == 3
    assert lead_payload["issues"][0]["title"].startswith("[Lead review]")
    assert lead_payload["clusters"][0]["keyword"] == "Anthropic news"
    assert lead_payload["clusters"][0]["priority_score"] >= lead_payload["clusters"][-1]["priority_score"]
    assert lead_payload["clusters"][0]["issue_count"] >= 1
    status_path = tmp_path / "out" / "review-queue" / "source-lead-review-status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert status_payload["count"] == 3
    assert status_payload["items"][0]["status"] == "pending"
    assert status_payload["items"][0]["lead_key"]


def test_cmd_build_review_queue_preserves_existing_lead_review_status(tmp_path: Path):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "latest-summary.json").write_text(
        json.dumps(_sample_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    governance_payload = _sample_governance_payload()
    (governance_dir / "source-governance.json").write_text(
        json.dumps(governance_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    review_queue_dir = tmp_path / "out" / "review-queue"
    review_queue_dir.mkdir(parents=True)
    (review_queue_dir / "source-lead-review-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T15:00:00+08:00",
                "count": 1,
                "items": [
                    {
                        "lead_key": "official_feed_leads|Anthropic news|Anthropic 官方博客|https://www.anthropic.com/news",
                        "status": "approved",
                        "note": "validated",
                        "updated_at": "2026-04-18T15:00:00+08:00",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    cmd_build_review_queue(tmp_path)

    status_path = review_queue_dir / "source-lead-review-status.json"
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    approved = next(item for item in status_payload["items"] if item["lead_key"].startswith("official_feed_leads|Anthropic news"))
    assert approved["status"] == "approved"
    assert approved["note"] == "validated"


def test_build_approved_source_lead_updates_extracts_actionable_candidates():
    issues = build_source_lead_review_candidates(_sample_governance_payload(), limit_per_kind=2)
    status_payload = {
        "items": [
            {
                "lead_key": issues[0]["meta"]["lead_key"],
                "status": "approved",
                "note": "use official feed first",
            },
            {
                "lead_key": issues[1]["meta"]["lead_key"],
                "status": "deferred",
                "note": "wait",
            },
        ]
    }

    updates = build_approved_source_lead_updates(issues, status_payload)

    assert len(updates) == 1
    assert updates[0]["lead_key"] == issues[0]["meta"]["lead_key"]
    assert updates[0]["status"] == "approved"
    assert updates[0]["target_kind"] in {"validated_listing", "official_feed", "rsshub", "changedetection"}
    assert updates[0]["source_id"] in {"anthropic-news", ""}
    assert "recommended_next_step" in updates[0]
    assert "apply_ready" in updates[0]
    assert "blocking_reason" in updates[0]


def test_build_approved_source_lead_updates_includes_anthropic_news_when_approved():
    payload = _sample_governance_payload()
    payload["official_feed_leads"][0]["feed_candidate"] = "https://www.anthropic.com/news/feed"
    issues = build_source_lead_review_candidates(payload, limit_per_kind=2)
    status_payload = {
        "items": [
            {
                "lead_key": issues[0]["meta"]["lead_key"],
                "status": "approved",
                "note": "anthropic ready",
            }
        ]
    }

    updates = build_approved_source_lead_updates(issues, status_payload)

    assert updates[0]["keyword"] in {"Anthropic news", "AI model safety blog"}
    assert "anthropic" in updates[0]["lead_key"].lower()
    assert updates[0]["candidate_value"] == "https://www.anthropic.com/news"
    assert updates[0]["source_id"] == "anthropic-news"
    assert updates[0]["remote_validation_required"] is False
    assert updates[0]["apply_ready"] is True
    assert updates[0]["blocking_reason"] == ""
