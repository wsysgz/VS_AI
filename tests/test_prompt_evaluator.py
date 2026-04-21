import json
from pathlib import Path

import pytest

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
    assert payload["dataset_meta"] == {}
    assert payload["summary"]["case_count"] == 3
    assert payload["leaderboard"][0]["stage"] in {"summary", "forecast", "domain_briefs"}
    assert payload["leaderboard"][0]["model"] == "offline-dataset"
    assert "overall_score_avg" in payload["leaderboard"][0]["metrics"]
    assert payload["leaderboard"][0]["prompt_id"]
    assert payload["cases"][0]["evaluations"][0]["metrics"]["required_fields_score"] >= 0


def test_evaluate_prompt_dataset_preserves_dataset_meta(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    dataset_path = tmp_path / "baseline-v1.json"
    dataset_path.write_text(
        json.dumps(
            {
                "meta": {
                    "dataset_id": "baseline-v1",
                    "version": "2026-04-12",
                    "description": "Repo managed prompt benchmark",
                },
                "cases": [],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    output_path = evaluate_prompt_dataset(tmp_path, dataset_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["dataset_meta"]["dataset_id"] == "baseline-v1"
    assert payload["dataset_meta"]["version"] == "2026-04-12"


def test_evaluate_prompt_dataset_emits_langfuse_root_case_and_generation_traces(tmp_path: Path, monkeypatch):
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
                                "prompt_id": "summary-v2",
                                "version": "v2",
                                "model": "offline-dataset",
                                "content": {
                                    "one_line_core": "Evaluation becomes core",
                                    "executive_summary": ["A", "B"],
                                    "key_points": [{"title": "Signal", "why_it_matters": "Matters"}],
                                    "key_insights": ["Insight"],
                                    "limitations": ["Need verification"],
                                    "actions": ["Track"],
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    trace_calls = {"root": [], "spans": [], "gens": [], "finishes": [], "flushes": 0}

    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_run_trace",
        lambda env, *, name, metadata: trace_calls["root"].append(
            {"env": env, "name": name, "metadata": metadata}
        )
        or {
            "enabled": True,
            "trace_id": "trace-123",
            "trace_url": "https://langfuse.example/trace/trace-123",
        },
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_stage_span",
        lambda name, parent_name=None, metadata=None: trace_calls["spans"].append(
            {"name": name, "parent_name": parent_name, "metadata": metadata}
        )
        or {"observation_id": name, "trace_id": "trace-123"},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_stage_span",
        lambda name, metadata=None, error=None: trace_calls["finishes"].append(
            {"name": name, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_generation_trace",
        lambda **kwargs: trace_calls["gens"].append(kwargs)
        or {"observation": object(), "capture_content": False},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_generation_trace",
        lambda trace_observation, output_text=None, metadata=None, usage_details=None, error=None: None,
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.complete_run_trace",
        lambda trace_state, metadata=None, error=None: trace_calls["root"].append(
            {"completed": True, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.flush_langfuse",
        lambda env=None: trace_calls.__setitem__("flushes", trace_calls["flushes"] + 1),
    )

    output_path = evaluate_prompt_dataset(
        tmp_path,
        dataset_path,
        env={
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 1
    assert trace_calls["root"][0]["name"] == "vs-ai-evaluate-prompts"
    assert trace_calls["root"][0]["metadata"]["timezone"] == "Asia/Shanghai"
    assert trace_calls["spans"][0]["name"] == "prompt-eval-case:summary-case"
    assert trace_calls["gens"][0]["stage"] == "prompt_eval"
    assert trace_calls["gens"][0]["parent_name"] == "prompt-eval-case:summary-case"
    assert trace_calls["gens"][0]["provider"] == "offline_eval"
    assert trace_calls["flushes"] == 1


def test_cmd_evaluate_prompts_passes_loaded_env(tmp_path: Path, monkeypatch):
    from auto_report.app import cmd_evaluate_prompts

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"cases": []}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        "auto_report.app.load_settings",
        lambda root_dir: type(
            "Settings",
            (),
            {"env": {"LANGFUSE_ENABLED": "true", "AUTO_TIMEZONE": "Asia/Shanghai"}},
        )(),
    )

    captured = {}

    def _fake_eval(root_dir, resolved_dataset_path, env=None):
        captured["root_dir"] = root_dir
        captured["dataset_path"] = resolved_dataset_path
        captured["env"] = env
        return tmp_path / "out.json"

    monkeypatch.setattr("auto_report.pipeline.prompt_evaluator.evaluate_prompt_dataset", _fake_eval)

    result = cmd_evaluate_prompts(tmp_path, str(dataset_path))

    assert result == tmp_path / "out.json"
    assert captured["dataset_path"] == dataset_path
    assert captured["env"]["LANGFUSE_ENABLED"] == "true"


def test_evaluate_prompt_dataset_marks_case_root_and_generation_trace_errors(tmp_path: Path, monkeypatch):
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
                        "reference": {"one_line_core": "Evaluation becomes core"},
                        "outputs": [
                            {
                                "prompt_id": "summary-v2",
                                "version": "v2",
                                "model": "offline-dataset",
                                "content": {"one_line_core": "Evaluation becomes core"},
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    trace_calls = {"root": [], "span_finishes": [], "generation_finishes": [], "flushes": 0}

    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_run_trace",
        lambda env, *, name, metadata: trace_calls["root"].append(
            {"env": env, "name": name, "metadata": metadata}
        )
        or {"enabled": True, "trace_id": "trace-123"},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_stage_span",
        lambda name, parent_name=None, metadata=None: {"observation_id": name, "trace_id": "trace-123"},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_stage_span",
        lambda name, metadata=None, error=None: trace_calls["span_finishes"].append(
            {"name": name, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_generation_trace",
        lambda **kwargs: {"observation": object(), "capture_content": False},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.finish_generation_trace",
        lambda trace_observation, output_text=None, metadata=None, usage_details=None, error=None: trace_calls[
            "generation_finishes"
        ].append(
            {
                "trace_observation": trace_observation,
                "output_text": output_text,
                "metadata": metadata,
                "usage_details": usage_details,
                "error": error,
            }
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.complete_run_trace",
        lambda trace_state, metadata=None, error=None: trace_calls["root"].append(
            {"completed": True, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.flush_langfuse",
        lambda env=None: trace_calls.__setitem__("flushes", trace_calls["flushes"] + 1),
    )

    def _raise_metric_error(*args, **kwargs):
        raise RuntimeError("metric boom")

    monkeypatch.setattr("auto_report.pipeline.prompt_evaluator._metric_bundle", _raise_metric_error)

    with pytest.raises(RuntimeError, match="metric boom"):
        evaluate_prompt_dataset(
            tmp_path,
            dataset_path,
            env={
                "LANGFUSE_ENABLED": "true",
                "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
                "LANGFUSE_SECRET_KEY": "sk-lf-test",
            },
        )

    assert trace_calls["span_finishes"][0]["name"] == "prompt-eval-case:summary-case"
    assert trace_calls["span_finishes"][0]["error"] == "metric boom"
    assert len(trace_calls["generation_finishes"]) == 1
    assert trace_calls["generation_finishes"][0]["error"] == "metric boom"
    assert trace_calls["root"][-1]["completed"] is True
    assert trace_calls["root"][-1]["error"] == "metric boom"
    assert trace_calls["flushes"] == 1


def test_evaluate_prompt_dataset_marks_root_trace_error_when_artifact_write_fails(tmp_path: Path, monkeypatch):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"cases": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    trace_calls = {"root": [], "flushes": 0}

    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.start_run_trace",
        lambda env, *, name, metadata: {"enabled": True, "trace_id": "trace-123"},
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.complete_run_trace",
        lambda trace_state, metadata=None, error=None: trace_calls["root"].append(
            {"completed": True, "metadata": metadata, "error": error}
        ),
    )
    monkeypatch.setattr(
        "auto_report.pipeline.prompt_evaluator.flush_langfuse",
        lambda env=None: trace_calls.__setitem__("flushes", trace_calls["flushes"] + 1),
    )

    original_write_text = Path.write_text

    def _raise_output_write_error(path: Path, *args, **kwargs):
        if path.name.startswith("prompt-eval-"):
            raise OSError("artifact write failed")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr("auto_report.pipeline.prompt_evaluator.Path.write_text", _raise_output_write_error)

    with pytest.raises(OSError, match="artifact write failed"):
        evaluate_prompt_dataset(
            tmp_path,
            dataset_path,
            env={
                "LANGFUSE_ENABLED": "true",
                "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
                "LANGFUSE_SECRET_KEY": "sk-lf-test",
            },
        )

    assert trace_calls["root"] == [
        {
            "completed": True,
            "metadata": {
                "dataset_path": str(dataset_path),
                "case_count": 0,
                "evaluation_count": 0,
            },
            "error": "artifact write failed",
        }
    ]
    assert trace_calls["flushes"] == 1
