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
    assert package.summary_payload["signals"][0]["lifecycle_state"] in {"new", "rising", "verified", "fading"}
    assert package.summary_payload["signals"][0]["risk_level"] in {"low", "medium", "high"}
    assert "mainline_memory" in package.summary_payload
    assert "lifecycle_summary" in package.summary_payload
    assert package.summary_payload["risk_level"] in {"low", "medium", "high"}
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


def test_build_report_package_wires_external_enrichment_fetcher_when_enabled(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    monkeypatch.setenv("EXTERNAL_ENRICHMENT_ENABLED", "true")
    monkeypatch.setenv("EXTERNAL_ENRICHMENT_MAX_SIGNALS", "1")
    monkeypatch.setenv("EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS", "7")

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.load_ai_readings",
        lambda root_dir: {"analysis": "a", "summary": "s", "forecast": "f"},
    )

    def fake_run_staged_ai_pipeline(**kwargs):
        return {
            "analyses": [
                {
                    "title": "Launch HN: Agent debugger",
                    "url": "https://news.ycombinator.com/item?id=1",
                    "primary_domain": "ai-llm-agent",
                    "confidence": "low",
                    "primary_contradiction": "vision vs evidence",
                    "core_insight": "Needs external corroboration.",
                }
            ],
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

    captured: dict[str, object] = {}

    def fake_apply_intelligence_layer(**kwargs):
        captured["has_external_fetcher"] = kwargs.get("external_enrichment_fetcher") is not None
        captured["external_enrichment_max_signals"] = kwargs.get("external_enrichment_max_signals")
        fetcher = kwargs.get("external_enrichment_fetcher")
        if fetcher is not None:
            fetched = fetcher(
                settings.root_dir,
                {
                    "title": "Launch HN: Agent debugger",
                    "url": "https://news.ycombinator.com/item?id=1",
                    "primary_domain": "ai-llm-agent",
                    "score": 3.2,
                },
            )
            captured["fetch_result"] = fetched
        return {
            "signals": kwargs["signals"],
            "analyses": kwargs["analyses"],
            "mainline_memory": [],
            "lifecycle_summary": {"new": 1, "rising": 0, "verified": 0, "fading": 0},
            "risk_level": "medium",
        }

    def fake_fetch_external_support_evidence(root_dir, signal, timeout_seconds=12):
        return [{"source_type": "paper", "title": f"timeout={timeout_seconds}", "url": "https://example.com/paper"}]

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.fetch_external_support_evidence",
        fake_fetch_external_support_evidence,
    )
    monkeypatch.setattr(
        "auto_report.pipeline.analysis.apply_intelligence_layer",
        fake_apply_intelligence_layer,
    )

    settings = load_settings(Path.cwd())
    items = [
        CollectedItem(
            source_id="hacker-news",
            item_id="1",
            title="Launch HN: Agent debugger",
            url="https://news.ycombinator.com/item?id=1",
            summary="Debugger tooling for agent workflows",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "debugger"],
            language="en",
            metadata={},
        )
    ]

    build_report_package(settings, items, diagnostics=[])

    assert captured["has_external_fetcher"] is True
    assert captured["external_enrichment_max_signals"] == 1
    assert captured["fetch_result"][0]["title"] == "timeout=7"


def test_build_report_package_surfaces_external_enrichment_metrics(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.load_ai_readings",
        lambda root_dir: {"analysis": "a", "summary": "s", "forecast": "f"},
    )

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.run_staged_ai_pipeline",
        lambda **kwargs: {
            "analyses": [
                {
                    "title": "Topic A",
                    "url": "https://example.com/a",
                    "primary_domain": "ai-llm-agent",
                    "confidence": "low",
                }
            ],
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
        },
    )

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.apply_intelligence_layer",
        lambda **kwargs: {
            "signals": kwargs["signals"],
            "analyses": kwargs["analyses"],
            "mainline_memory": [],
            "lifecycle_summary": {"new": 1, "rising": 0, "verified": 0, "fading": 0},
            "risk_level": "medium",
            "external_enrichment": {
                "enabled": True,
                "max_signals": 2,
                "attempted": 2,
                "succeeded": 1,
                "failed": 1,
                "skipped": 0,
                "budget_used": 2,
                "success_rate": 0.5,
                "circuit_open": False,
                "reasons": ["empty-result: Topic B"],
            },
        },
    )

    settings = load_settings(Path.cwd())
    items = [
        CollectedItem(
            source_id="hacker-news",
            item_id="1",
            title="Topic A",
            url="https://example.com/a",
            summary="Debugger tooling for agent workflows",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "debugger"],
            language="en",
            metadata={},
        )
    ]

    package = build_report_package(settings, items, diagnostics=[])

    assert package.external_enrichment["attempted"] == 2
    assert package.external_enrichment["success_rate"] == 0.5


def test_build_report_package_keeps_collector_diagnostics_out_of_public_limitations(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.load_ai_readings",
        lambda root_dir: {"analysis": "a", "summary": "s", "forecast": "f"},
    )

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.run_staged_ai_pipeline",
        lambda **kwargs: {
            "analyses": [
                {
                    "title": "Topic A",
                    "url": "https://example.com/a",
                    "primary_domain": "ai-llm-agent",
                    "confidence": "low",
                }
            ],
            "summary": {
                "one_line_core": "core",
                "executive_summary": [],
                "key_points": [],
                "key_insights": [],
                "limitations": ["部分主题仍需人工复核"],
                "actions": [],
            },
            "forecast": {"forecast_conclusion": "watch"},
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
            "ai_metrics": {
                "provider": "",
                "model": "",
                "calls": 0,
                "token_usage": {"prompt": 0, "completion": 0, "total": 0},
                "latency_seconds": 0.0,
                "fallback_stages": [],
            },
        },
    )

    monkeypatch.setattr(
        "auto_report.pipeline.analysis.apply_intelligence_layer",
        lambda **kwargs: {
            "signals": kwargs["signals"],
            "analyses": kwargs["analyses"],
            "mainline_memory": [],
            "lifecycle_summary": {"new": 1, "rising": 0, "verified": 0, "fading": 0},
            "risk_level": "medium",
            "external_enrichment": {
                "enabled": False,
                "max_signals": 0,
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
                "skipped": 0,
                "budget_used": 0,
                "success_rate": 0.0,
                "circuit_open": False,
                "reasons": [],
            },
        },
    )

    settings = load_settings(Path.cwd())
    items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Topic A",
            url="https://example.com/a",
            summary="Debugger tooling for agent workflows",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "debugger"],
            language="en",
            metadata={},
        )
    ]

    package = build_report_package(
        settings,
        items,
        diagnostics=["RSS source failed: openai-news -> 404 Client Error: Not Found"],
    )

    assert package.summary_payload["limitations"] == ["部分主题仍需人工复核"]
    assert package.summary_payload["risks"] == ["RSS source failed: openai-news -> 404 Client Error: Not Found"]
