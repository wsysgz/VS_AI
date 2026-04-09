from pathlib import Path

from auto_report.models.records import CollectedItem
from auto_report.pipeline.analysis import build_report_package
from auto_report.settings import load_settings


def test_build_report_package_generates_domain_signals():
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
