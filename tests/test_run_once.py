import shutil
from pathlib import Path

from auto_report.app import render_reports
from auto_report.models.records import CollectedItem
from auto_report.pipeline.run_once import build_run_status


def test_build_run_status_tracks_generated_outputs():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
    )

    assert status["generated_files"] == ["data/reports/latest-summary.md"]
    assert status["pushed"] is False


def test_render_reports_writes_chinese_summary_files(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    sample_items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Agent platform launched",
            url="https://example.com/agent-platform",
            summary="A new reasoning agent stack for enterprise deployment",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "reasoning"],
            language="en",
            metadata={},
        )
    ]

    monkeypatch.setattr(
        "auto_report.app.collect_all_items",
        lambda settings: (sample_items, ["测试诊断"]),
    )

    generated_files = render_reports(tmp_path)

    assert any(path.endswith("latest-summary.md") for path in generated_files)
    content = (tmp_path / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8")
    assert "自动情报快报" in content
