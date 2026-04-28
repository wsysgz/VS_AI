import json
import shutil
from pathlib import Path

from auto_report.outputs.ops_dashboard import build_ops_dashboard


def test_build_ops_dashboard_writes_private_dashboard(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-11T07:30:00+08:00",
                "pushed": False,
                "push_channel": "",
                "scheduler": {
                    "trigger_kind": "compensation",
                    "compensation_run": True,
                },
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": ["feishu"],
                    "skipped_channels": [],
                    "channels": {
                        "feishu": {
                            "status": "error",
                            "detail": "request timed out",
                            "error_type": "network",
                            "attempted_at": "2026-04-11T07:29:00+08:00",
                        },
                    },
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "fallback"},
                "source_stats": {"collected_items": 12, "report_topics": 4},
                "timings": {"collection": 2.4, "rendering": 0.8},
                "source_health": {
                    "total": 2,
                    "not_found": 1,
                    "timeout": 1,
                    "request_error": 0,
                    "other": 0,
                    "samples": [
                        "RSS source failed: openai-news -> 404 Client Error: Not Found",
                        "Website collectors timed out: openai-blog",
                    ],
                    "sources": {
                        "openai-news": {
                            "collector": "rss",
                            "stability_tier": "stable-feed",
                            "replacement_hint": "",
                            "failure_count": 1,
                            "error_categories": ["not_found"],
                            "last_error": "RSS source failed: openai-news -> 404 Client Error: Not Found",
                        },
                        "openai-blog": {
                            "collector": "websites",
                            "stability_tier": "fragile-listing",
                            "replacement_hint": "Replace with a stable listing page",
                            "failure_count": 1,
                            "error_categories": ["timeout"],
                            "last_error": "Website collectors timed out: openai-blog",
                        },
                    },
                },
                "ai_metrics": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "calls": 3,
                    "token_usage": {"prompt": 120, "completion": 60, "total": 180},
                    "latency_seconds": 4.2,
                    "fallback_stages": ["forecast"],
                },
                "review": {
                    "reviewer": "Alice",
                    "review_note": "checked key sources",
                },
            }
        ),
        encoding="utf-8",
    )

    output_path = build_ops_dashboard(tmp_path)

    assert output_path == tmp_path / "out" / "ops-dashboard" / "index.html"
    html = output_path.read_text(encoding="utf-8")
    assert "Operations Dashboard" in html
    assert "compensation" in html
    assert "feishu" in html
    assert "network" in html
    assert "request timed out" in html
    assert "AI Metrics" in html
    assert "gpt-4o-mini" in html
    assert "180" in html
    assert "Source Health" in html
    assert "Source Failure Breakdown" in html
    assert "Replacement Hint" in html
    assert "Review Metadata" in html
    assert "checked key sources" in html
    assert "openai-blog" in html
    assert "fragile-listing" in html
    assert "Replace with a stable listing page" in html


def test_build_ops_dashboard_renders_prompt_eval_history_and_regression_watch(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-11T07:30:00+08:00",
                "pushed": True,
                "push_channel": "feishu",
                "risk_level": "medium",
                "scheduler": {"trigger_kind": "schedule", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": ["feishu"],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {
                        "feishu": {
                            "status": "ok",
                            "detail": "1 message(s)",
                            "error_type": None,
                            "attempted_at": "2026-04-11T07:29:05+08:00",
                        }
                    },
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 8, "report_topics": 3},
                "timings": {"collection": 1.8, "rendering": 0.4},
            }
        ),
        encoding="utf-8",
    )

    evals_dir = tmp_path / "out" / "evals"
    evals_dir.mkdir(parents=True)
    (evals_dir / "prompt-eval-20260411-070000.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-11T07:00:00+08:00",
                "dataset_path": "config/prompt_eval/baseline-v1.json",
                "dataset_meta": {"dataset_id": "baseline-v1", "version": "2026-04-12"},
                "summary": {"case_count": 3, "evaluation_count": 3, "stage_count": 1},
                "leaderboard": [
                    {
                        "stage": "summary",
                        "prompt_id": "summary-v7",
                        "version": "v7.0.0",
                        "model": "offline-dataset",
                        "tags": ["baseline"],
                        "case_count": 3,
                        "metrics": {"overall_score_avg": 0.92},
                    }
                ],
                "cases": [],
            }
        ),
        encoding="utf-8",
    )
    (evals_dir / "prompt-eval-20260411-073000.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-11T07:30:00+08:00",
                "dataset_path": "config/prompt_eval/baseline-v1.json",
                "dataset_meta": {"dataset_id": "baseline-v1", "version": "2026-04-12"},
                "summary": {"case_count": 3, "evaluation_count": 3, "stage_count": 1},
                "leaderboard": [
                    {
                        "stage": "summary",
                        "prompt_id": "summary-v7",
                        "version": "v7.0.1",
                        "model": "offline-dataset",
                        "tags": ["candidate"],
                        "case_count": 3,
                        "metrics": {"overall_score_avg": 0.81},
                    }
                ],
                "cases": [],
            }
        ),
        encoding="utf-8",
    )

    output_path = build_ops_dashboard(tmp_path)

    html = output_path.read_text(encoding="utf-8")
    assert "Prompt Evaluation Trend" in html
    assert "Prompt Regression Watch" in html
    assert "summary-v7" in html
    assert "v7.0.1" in html
    assert "v7.0.0" in html
    assert "-0.11" in html
    assert "baseline-v1" in html


def test_build_ops_dashboard_renders_external_enrichment_section(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-12T07:30:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "medium",
                "scheduler": {"trigger_kind": "schedule", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {},
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 8, "report_topics": 3},
                "timings": {"collection": 1.8, "rendering": 0.4},
                "external_enrichment": {
                    "enabled": True,
                    "max_signals": 2,
                    "attempted": 2,
                    "succeeded": 1,
                    "failed": 1,
                    "skipped": 1,
                    "budget_used": 2,
                    "success_rate": 0.5,
                    "circuit_open": True,
                    "reasons": ["empty-result: Topic B", "circuit-open: Topic C"],
                },
            }
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "External Enrichment" in html
    assert "Topic B" in html
    assert "Topic C" in html
    assert "0.50" in html
    assert "open" in html


def test_build_ops_dashboard_renders_source_registry_from_config(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T08:00:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "low",
                "scheduler": {"trigger_kind": "manual", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {},
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 0, "report_topics": 0},
                "timings": {},
            }
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Source Registry" in html
    assert "anthropic-news" in html
    assert "NVIDIA/TensorRT" in html
    assert "hacker_news" in html
    assert "fragile-listing" in html
    assert "stable-feed" in html
    assert "dynamic-site" in html
    assert "manual-watch" in html
    assert "listing-poll" in html
    assert "repo-poll" in html
    assert "manual-review" in html
    assert "rsshub-or-feed" in html
    assert "nxp-appcodehub/dm-eiq-genai-flow-demonstrator" in html
    assert "Manual Review Focus" in html
    assert "No manual-review sources" in html
    assert "nxp-edge-ai" not in html.split("Manual Review Focus", 1)[1]
    assert "meta-ai-blog" not in html.split("Manual Review Focus", 1)[1]
    assert "st-blog" not in html.split("Manual Review Focus", 1)[1]
    assert "ti-e2e-blog" not in html.split("Manual Review Focus", 1)[1]
    assert "Source Governance Queue" in html
    assert "Governance Priority Queue" in html
    assert "Priority" in html
    assert "RSSHub Candidates" in html
    assert "changedetection Candidates" in html
    assert "Replacement Candidates" in html
    assert "google-ai-edge" in html


def test_build_ops_dashboard_renders_local_watch_registry_and_results(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:30:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "low",
                "scheduler": {"trigger_kind": "manual", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {},
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 0, "report_topics": 0},
                "timings": {},
            }
        ),
        encoding="utf-8",
    )
    governance_dir = tmp_path / "out" / "source-governance"
    governance_dir.mkdir(parents=True)
    (governance_dir / "changedetection-watch-registry.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:30:00+08:00",
                "count": 1,
                "summary": {"status_counts": {"active_local": 1}},
                "items": [
                    {
                        "source_id": "qualcomm-onq",
                        "watch_target": "https://www.qualcomm.com/news/onq",
                        "priority_score": 90,
                        "priority_label": "high",
                        "status": "active_local",
                        "note": "managed locally",
                        "next_action": "Run local watch checks.",
                        "updated_at": "2026-04-21T18:30:00+08:00",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (governance_dir / "watch-run-results.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-21T18:35:00+08:00",
                "summary": {
                    "active_watch_count": 1,
                    "initialized_count": 0,
                    "changed_count": 1,
                    "unchanged_count": 0,
                    "blocked_count": 0,
                },
                "items": [
                    {
                        "source_id": "qualcomm-onq",
                        "status": "changed",
                        "checked_at": "2026-04-21T18:35:00+08:00",
                        "new_item_count": 1,
                        "new_items": [{"title": "New Post", "url": "https://www.qualcomm.com/news/onq/new"}],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Local Watch Registry" in html
    assert "Local Watch Run Results" in html
    assert "qualcomm-onq" in html
    assert "active_local" in html
    assert "managed locally" in html
    assert "changed" in html
    assert "New Post" in html


def test_build_ops_dashboard_prefers_source_registry_from_run_status(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-17T09:00:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "low",
                "scheduler": {"trigger_kind": "manual", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {},
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 0, "report_topics": 0},
                "timings": {},
                "source_registry": {
                    "custom-source": {
                        "collector": "rss",
                        "enabled": True,
                        "mode": "rss_feed",
                        "source_group": "custom-source",
                        "stability_tier": "stable-feed",
                        "replacement_hint": "Keep the live feed",
                        "watch_strategy": "feed-poll",
                        "replacement_target": "none",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Source Registry" in html
    assert "custom-source" in html
    assert "Keep the live feed" in html
    assert "feed-poll" in html


def test_build_ops_dashboard_renders_discovery_leads(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T13:30:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "low",
                "scheduler": {"trigger_kind": "manual", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": [],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {},
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 0, "report_topics": 0},
                "timings": {},
                "source_governance": {"summary": {}},
                "official_feed_leads": [
                    {
                        "keyword": "Jetson edge AI",
                        "title": "NVIDIA Jetson Blog Feed",
                        "url": "https://developer.nvidia.com/blog/tag/jetson/feed/",
                        "classification": "official-feed",
                        "confidence": "high",
                        "feed_candidate": "https://developer.nvidia.com/blog/tag/jetson/feed/",
                        "next_action": "Promote to rss source after validation",
                    }
                ],
                "rsshub_leads": [
                    {
                        "keyword": "Anthropic news",
                        "title": "Anthropic RSSHub",
                        "url": "https://rsshub.app/anthropic/news",
                        "classification": "rsshub-candidate",
                        "confidence": "medium",
                        "rsshub_candidate": "/anthropic/news",
                        "next_action": "Validate RSSHub route",
                    }
                ],
                "changedetection_leads": [
                    {
                        "keyword": "Anthropic news",
                        "title": "Anthropic News",
                        "url": "https://www.anthropic.com/news",
                        "classification": "changedetection-candidate",
                        "confidence": "high",
                        "changedetection_candidate": "https://www.anthropic.com/news",
                        "next_action": "Create changedetection watch",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")

    assert "Discovery Leads" in html
    assert "Official Feed Leads" in html
    assert "RSSHub Leads" in html
    assert "changedetection Leads" in html
    assert "Jetson edge AI" in html
    assert "/anthropic/news" in html
    assert "Create changedetection watch" in html
