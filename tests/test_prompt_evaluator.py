import json
from pathlib import Path

from auto_report.pipeline.prompt_evaluator import evaluate_prompt_dataset


def test_evaluate_prompt_dataset_outputs_stage_prompt_model_metrics(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "summary-case",
                        "stage": "summary",
                        "reference": {
                            "one_line_core": "Evaluation becomes core",
                            "executive_summary": ["A", "B"],
                            "key_points": [{"title": "Signal", "why_it_matters": "Matters"}],
                            "key_insights": ["Insight"],
                            "limitations": ["Need verification"],
                            "actions": ["Track"],
                        },
                        "outputs": [
                            {
                                "prompt_id": "summary-legacy",
                                "version": "legacy",
                                "model": "offline-dataset",
                                "content": {
                                    "one_line_core": "Evaluation becomes core",
                                    "executive_summary": ["A", "B"],
                                    "key_points": [{"title": "Signal", "why_it_matters": "Matters"}],
                                    "key_insights": ["Insight"],
                                    "limitations": ["Need verification"],
                                    "actions": ["Track"],
                                },
                            },
                            {
                                "prompt_id": "summary-v2",
                                "version": "v2",
                                "model": "offline-dataset",
                                "content": {
                                    "one_line_core": "Core only",
                                    "executive_summary": [],
                                },
                            },
                        ],
                    },
                    {
                        "id": "forecast-case",
                        "stage": "forecast",
                        "reference": {
                            "best_case": "Best",
                            "worst_case": "Worst",
                            "most_likely_case": "Likely",
                            "key_variables": ["Variable"],
                            "forecast_conclusion": "Conclusion",
                            "confidence": "medium",
                        },
                        "outputs": [
                            {
                                "prompt_id": "forecast-v2",
                                "version": "v2",
                                "model": "offline-dataset",
                                "content": {
                                    "best_case": "Best",
                                    "worst_case": "Worst",
                                    "most_likely_case": "Likely",
                                    "key_variables": ["Variable"],
                                    "forecast_conclusion": "Conclusion",
                                    "confidence": "medium",
                                },
                            }
                        ],
                    },
                    {
                        "id": "domain-brief-case",
                        "stage": "domain_briefs",
                        "reference": {
                            "title": "AI / Agent",
                            "one_line_core": "Domain momentum",
                            "executive_summary": ["A"],
                            "signals": [{"title": "Signal A"}],
                        },
                        "outputs": [
                            {
                                "prompt_id": "domain-briefs-v1",
                                "version": "v1",
                                "model": "offline-dataset",
                                "content": {
                                    "title": "AI / Agent",
                                    "one_line_core": "Domain momentum",
                                    "executive_summary": ["A"],
                                    "signals": [{"title": "Signal A"}],
                                },
                            }
                        ],
                    },
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = evaluate_prompt_dataset(tmp_path, dataset_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.parent.name == "evals"
    assert payload["dataset_path"].endswith("dataset.json")
    assert payload["summary"]["case_count"] == 3
    assert payload["leaderboard"][0]["stage"] in {"summary", "forecast", "domain_briefs"}
    assert payload["leaderboard"][0]["model"] == "offline-dataset"
    assert "overall_score_avg" in payload["leaderboard"][0]["metrics"]
    assert payload["leaderboard"][0]["prompt_id"]
    assert payload["cases"][0]["evaluations"][0]["metrics"]["required_fields_score"] >= 0
