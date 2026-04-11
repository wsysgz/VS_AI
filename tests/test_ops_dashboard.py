import json
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
                    "successful_channels": ["telegram"],
                    "failed_channels": ["pushplus"],
                    "skipped_channels": ["feishu"],
                    "channels": {
                        "pushplus": {
                            "status": "error",
                            "detail": "request timed out",
                            "error_type": "network",
                            "attempted_at": "2026-04-11T07:29:00+08:00",
                        },
                        "telegram": {
                            "status": "ok",
                            "detail": "1 message(s)",
                            "error_type": None,
                            "attempted_at": "2026-04-11T07:29:05+08:00",
                        },
                        "feishu": {
                            "status": "skipped",
                            "detail": "missing config",
                            "error_type": None,
                            "attempted_at": None,
                        },
                    },
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "fallback"},
                "source_stats": {"collected_items": 12, "filtered_topics": 4},
                "timings": {"collection": 2.4, "rendering": 0.8},
            }
        ),
        encoding="utf-8",
    )

    output_path = build_ops_dashboard(tmp_path)

    assert output_path == tmp_path / "out" / "ops-dashboard" / "index.html"
    html = output_path.read_text(encoding="utf-8")
    assert "Operations Dashboard" in html
    assert "compensation" in html
    assert "pushplus" in html
    assert "network" in html
    assert "request timed out" in html


def test_build_ops_dashboard_renders_prompt_eval_history_and_regression_watch(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-11T07:30:00+08:00",
                "pushed": True,
                "push_channel": "telegram",
                "risk_level": "medium",
                "scheduler": {"trigger_kind": "schedule", "compensation_run": False},
                "delivery_results": {
                    "successful_channels": ["telegram"],
                    "failed_channels": [],
                    "skipped_channels": [],
                    "channels": {
                        "telegram": {
                            "status": "ok",
                            "detail": "1 message(s)",
                            "error_type": None,
                            "attempted_at": "2026-04-11T07:29:05+08:00",
                        }
                    },
                },
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 8, "filtered_topics": 3},
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
                "dataset_path": "fixtures/baseline.json",
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
                "dataset_path": "fixtures/baseline.json",
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
    assert "fixtures/baseline.json" in html


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
                "source_stats": {"collected_items": 8, "filtered_topics": 3},
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
