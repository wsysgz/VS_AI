from pathlib import Path

from auto_report.models.records import CollectedItem
from auto_report.pipeline.analysis import build_report_package
from auto_report.settings import load_settings


def test_build_report_package_generates_domain_signals(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    settings = load_settings(Path.cwd())
    items = [
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
        ),
        CollectedItem(
            source_id="web",
            item_id="2",
            title="Edge AI NPU announced",
            url="https://example.com/npu-launch",
            summary="Embedded accelerator for industrial cameras",
            published_at="2026-04-09T00:10:00+00:00",
            collected_at="2026-04-09T01:10:00+00:00",
            tags=["npu", "edge ai"],
            language="en",
            metadata={},
        ),
    ]

    package = build_report_package(settings, items, diagnostics=["rss ok"])

    assert len(package.signals) == 2
    assert package.summary_payload["meta"]["total_topics"] == 2
    assert package.summary_payload["signals"][0]["evidence_count"] >= 1
    assert "ai-llm-agent" in package.domain_payloads
    assert "ai-x-electronics" in package.domain_payloads


def test_build_report_package_enables_ai_for_openai_provider(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.load_ai_readings",
        lambda root_dir: {"analysis": "a", "summary": "s", "forecast": "f"},
    )

    def fake_run_staged_ai_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "analyses": [],
            "summary": {
                "one_line_core": "core",
                "executive_summary": [],
                "key_points": [],
                "key_insights": [],
                "limitations": [],
                "actions": [],
            },
            "forecast": {"forecast_conclusion": "watch"},
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
        }

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.run_staged_ai_pipeline",
        fake_run_staged_ai_pipeline,
    )

    settings = load_settings(Path.cwd())
    items = [
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

    build_report_package(settings, items, diagnostics=[])

    assert captured["ai_enabled"] is True
