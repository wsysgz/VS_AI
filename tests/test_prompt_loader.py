from pathlib import Path

from auto_report.pipeline.prompt_loader import load_ai_readings


def test_load_ai_readings_returns_all_stage_texts(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    readings = load_ai_readings(tmp_path)

    assert readings["analysis"] == "analysis-rules"
    assert readings["summary"] == "summary-rules"
    assert readings["forecast"] == "forecast-rules"
