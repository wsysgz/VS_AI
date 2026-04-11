from pathlib import Path

import json

from auto_report.pipeline.prompt_loader import load_ai_readings, load_prompt_registry


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


def test_load_prompt_registry_supports_versioned_manifest_and_active_prompt(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-v2.md").write_text("analysis-v2-rules", encoding="utf-8")
    (ai_dir / "summary-v2.md").write_text("summary-v2-rules", encoding="utf-8")
    (ai_dir / "forecast-v2.md").write_text("forecast-v2-rules", encoding="utf-8")
    (ai_dir / "domain-briefs-v1.md").write_text("domain-briefs-v1-rules", encoding="utf-8")
    (ai_dir / "registry.json").write_text(
        json.dumps(
            {
                "analysis": [
                    {
                        "id": "analysis-v2",
                        "version": "v2",
                        "path": "analysis-v2.md",
                        "tags": ["prod", "baseline"],
                        "active": True,
                    }
                ],
                "summary": [
                    {
                        "id": "summary-v2",
                        "version": "v2",
                        "path": "summary-v2.md",
                        "tags": ["prod"],
                        "active": True,
                    }
                ],
                "forecast": [
                    {
                        "id": "forecast-v2",
                        "version": "v2",
                        "path": "forecast-v2.md",
                        "tags": ["prod"],
                        "active": True,
                    }
                ],
                "domain_briefs": [
                    {
                        "id": "domain-briefs-v1",
                        "version": "v1",
                        "path": "domain-briefs-v1.md",
                        "tags": ["eval"],
                        "active": True,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    registry = load_prompt_registry(tmp_path)
    readings = load_ai_readings(tmp_path)

    assert registry["summary"][0]["id"] == "summary-v2"
    assert registry["summary"][0]["tags"] == ["prod"]
    assert registry["domain_briefs"][0]["content"] == "domain-briefs-v1-rules"
    assert readings["analysis"] == "analysis-v2-rules"
    assert readings["summary"] == "summary-v2-rules"
    assert readings["forecast"] == "forecast-v2-rules"


def test_load_prompt_registry_falls_back_to_legacy_files(tmp_path: Path):
    ai_dir = tmp_path / "config" / "ai_reading"
    ai_dir.mkdir(parents=True)
    (ai_dir / "analysis-before.md").write_text("analysis-rules", encoding="utf-8")
    (ai_dir / "summary-before.md").write_text("summary-rules", encoding="utf-8")
    (ai_dir / "forecast-before.md").write_text("forecast-rules", encoding="utf-8")

    registry = load_prompt_registry(tmp_path)

    assert registry["analysis"][0]["id"] == "analysis-legacy"
    assert registry["analysis"][0]["version"] == "legacy"
    assert registry["analysis"][0]["tags"] == ["compat"]
