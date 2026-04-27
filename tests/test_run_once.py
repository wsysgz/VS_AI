import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from auto_report.app import cmd_analyze_only, cmd_diagnose_delivery, cmd_sync_feishu_workspace, run_once
from auto_report.app import render_reports
from auto_report.models.records import CollectedItem
from auto_report.pipeline.run_once import build_run_status


class _FrozenAppDateTime:
    _fixed_utc = datetime(2026, 4, 12, 23, 59, 54, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return cls._fixed_utc.astimezone(tz)
        return cls._FrozenNow(cls._fixed_utc)

    class _FrozenNow:
        def __init__(self, value: datetime):
            self._value = value

        def astimezone(self, tz=None):
            if tz is None:
                return self._value
            return self._value.astimezone(tz)


class _FrozenStatusDateTime:
    _fixed_utc = datetime(2026, 4, 12, 23, 59, 54, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls._fixed_utc
        return cls._fixed_utc.astimezone(tz)


def test_build_run_status_tracks_generated_outputs():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
    )

    assert status["generated_files"] == ["data/reports/latest-summary.md"]
    assert status["pushed"] is False


def test_build_run_status_includes_stage_status_and_source_counts():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        stage_status={"analysis": "ok", "summary": "fallback", "forecast": "fallback"},
        source_stats={"collected_items": 12, "report_topics": 5},
    )

    assert status["stage_status"]["analysis"] == "ok"
    assert status["source_stats"]["report_topics"] == 5


def test_build_run_status_includes_scheduler_context():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        scheduler={"trigger_kind": "compensation", "compensation_run": True},
    )

    assert status["scheduler"] == {
        "trigger_kind": "compensation",
        "compensation_run": True,
    }


def test_build_run_status_ignores_retired_delivery_responses():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        push_channel="feishu",
        push_response={
            "pushplus": {"code": 200, "msg": "retired"},
            "telegram": [{"ok": True, "result": {"message_id": 7}}],
            "feishu": [{"code": 0, "msg": "success", "data": {"message_id": "om_1"}}],
        },
    )

    assert status["push_response"] == {
        "feishu": {
            "ok": True,
            "messages_sent": 1,
            "message_ids": ["om_1"],
            "description": "success",
        }
    }


def test_build_run_status_summarizes_feishu_responses():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        push_response={
            "feishu": [
                {
                    "code": 0,
                    "msg": "success",
                    "data": {"message_id": "om_1"},
                },
                {
                    "code": 0,
                    "msg": "success",
                    "data": {"message_id": "om_2"},
                },
            ]
        },
    )

    assert status["push_response"]["feishu"] == {
        "ok": True,
        "messages_sent": 2,
        "message_ids": ["om_1", "om_2"],
        "description": "success",
    }


def test_build_run_status_preserves_feishu_delivery_kind():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        push_response={
            "feishu": [
                {
                    "code": 0,
                    "msg": "success",
                    "data": {"message_id": "om_1"},
                    "delivery_kind": "card_success",
                }
            ]
        },
    )

    assert status["push_response"]["feishu"]["delivery_kind"] == "card_success"


def test_build_run_status_includes_external_enrichment_metrics():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        external_enrichment={
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
    )

    assert status["external_enrichment"]["attempted"] == 2
    assert status["external_enrichment"]["success_rate"] == 0.5


def test_build_run_status_includes_ai_metrics():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        ai_metrics={
            "provider": "openai",
            "model": "gpt-4o-mini",
            "calls": 3,
            "token_usage": {"prompt": 120, "completion": 60, "total": 180},
            "latency_seconds": 4.2,
            "fallback_stages": ["forecast"],
        },
    )

    assert status["ai_metrics"]["provider"] == "openai"
    assert status["ai_metrics"]["token_usage"]["total"] == 180
    assert status["ai_metrics"]["fallback_stages"] == ["forecast"]


def test_build_run_status_includes_source_health_and_review_metadata():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        source_health={
            "total": 2,
            "not_found": 1,
            "timeout": 1,
            "request_error": 0,
            "other": 0,
            "samples": [
                "RSS source failed: openai-news -> 404 Client Error: Not Found",
                "Website collectors timed out: openai-blog",
            ],
        },
        review={
            "reviewer": "Alice",
            "review_note": "checked key sources",
        },
    )

    assert status["source_health"]["not_found"] == 1
    assert status["source_health"]["timeout"] == 1
    assert status["review"]["reviewer"] == "Alice"
    assert status["review"]["review_note"] == "checked key sources"


def test_build_run_status_includes_source_registry():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        source_registry={
            "meta-ai-blog": {
                "collector": "rss",
                "enabled": True,
                "mode": "rss_feed",
                "stability_tier": "manual-watch",
                "replacement_hint": "Confirm a live Meta AI feed or disable this slot",
                "watch_strategy": "manual-review",
                "replacement_target": "official-meta-feed",
            }
        },
    )

    assert status["source_registry"]["meta-ai-blog"]["collector"] == "rss"
    assert status["source_registry"]["meta-ai-blog"]["stability_tier"] == "manual-watch"
    assert status["source_registry"]["meta-ai-blog"]["watch_strategy"] == "manual-review"
    assert status["source_registry"]["meta-ai-blog"]["replacement_target"] == "official-meta-feed"


def test_build_run_status_includes_source_governance():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        source_governance={
            "summary": {
                "manual_review_count": 1,
                "rsshub_candidate_count": 1,
                "changedetection_candidate_count": 1,
                "replacement_candidate_count": 1,
            },
            "manual_review": [
                {"source_id": "st-blog", "replacement_target": "rsshub-or-stable-listing"}
            ],
            "rsshub_candidates": [
                {"source_id": "st-blog", "replacement_target": "rsshub-or-stable-listing"}
            ],
            "changedetection_candidates": [
                {"source_id": "google-ai-edge", "candidate_kind": "changedetection_watch"}
            ],
            "replacement_candidates": [
                {"source_id": "st-blog", "replacement_target": "rsshub-or-stable-listing"}
            ],
        },
    )

    assert status["source_governance"]["summary"]["manual_review_count"] == 1
    assert status["source_governance"]["summary"]["changedetection_candidate_count"] == 1
    assert status["source_governance"]["rsshub_candidates"][0]["source_id"] == "st-blog"
    assert status["source_governance"]["changedetection_candidates"][0]["source_id"] == "google-ai-edge"


def test_build_run_status_defaults_source_governance_changedetection_fields():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
    )

    assert status["source_governance"]["summary"]["changedetection_candidate_count"] == 0
    assert status["source_governance"]["changedetection_candidates"] == []


def test_build_run_status_includes_tracing_metadata():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        tracing={
            "enabled": True,
            "trace_id": "trace-123",
            "trace_url": "https://langfuse.example/trace/trace-123",
        },
    )

    assert status["tracing"]["enabled"] is True
    assert status["tracing"]["trace_id"] == "trace-123"
    assert status["tracing"]["trace_url"] == "https://langfuse.example/trace/trace-123"


def test_build_run_status_preserves_backup_and_guardrail_ai_metrics():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        ai_metrics={
            "provider": "mixed",
            "model": "mixed",
            "calls": 2,
            "token_usage": {"prompt": 20, "completion": 8, "total": 28},
            "latency_seconds": 1.2,
            "fallback_stages": [],
            "backup_stages": ["analysis"],
            "guardrail_stages": ["analysis"],
            "stage_breakdown": {
                "analysis": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "calls": 2,
                    "token_usage": {"prompt": 20, "completion": 8, "total": 28},
                    "latency_seconds": 1.2,
                    "attempts": 2,
                    "backup_used": True,
                    "guardrail_triggered": True,
                    "guardrail_reason": "latency_exceeded",
                    "primary_provider": "deepseek",
                    "primary_model": "deepseek-chat",
                    "final_provider": "openai",
                    "final_model": "gpt-4o-mini",
                    "budget": {"max_latency_seconds": 0.5, "max_total_tokens": 1000},
                }
            },
        },
    )

    stage = status["ai_metrics"]["stage_breakdown"]["analysis"]
    assert status["ai_metrics"]["backup_stages"] == ["analysis"]
    assert status["ai_metrics"]["guardrail_stages"] == ["analysis"]
    assert stage["attempts"] == 2
    assert stage["backup_used"] is True
    assert stage["guardrail_reason"] == "latency_exceeded"
    assert stage["budget"]["max_latency_seconds"] == 0.5


def test_build_run_status_includes_publication_mode():
    status = build_run_status(
        generated_files=["data/reports/latest-summary-reviewed.md"],
        pushed=False,
        publication_mode="reviewed",
    )

    assert status["publication_mode"] == "reviewed"


def test_render_reports_writes_executive_brief_markdown(tmp_path, monkeypatch):
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

    generated_files, _, _ = render_reports(tmp_path)

    assert any(path.endswith("latest-summary.md") for path in generated_files)
    content = (tmp_path / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8")
    assert "自动情报快报" in content
    assert "## 一句话判断" in content
    assert "## 重点主线" in content
    assert "## 行动建议" in content


def test_render_reports_writes_reviewed_track_outputs(tmp_path, monkeypatch):
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

    generated_files, _, _ = render_reports(tmp_path, publication_mode="reviewed")

    reviewed_json = tmp_path / "data" / "reports" / "latest-summary-reviewed.json"
    payload = json.loads(reviewed_json.read_text(encoding="utf-8"))

    assert any(path.endswith("latest-summary-reviewed.json") for path in generated_files)
    assert payload["meta"]["publication_mode"] == "reviewed"


def test_render_reports_writes_review_metadata_into_report_meta(tmp_path, monkeypatch):
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

    render_reports(
        tmp_path,
        publication_mode="reviewed",
        reviewer="Alice",
        review_note="checked key sources",
    )

    payload = json.loads((tmp_path / "data" / "reports" / "latest-summary-reviewed.json").read_text(encoding="utf-8"))

    assert payload["meta"]["review"]["reviewer"] == "Alice"
    assert payload["meta"]["review"]["review_note"] == "checked key sources"


def test_render_reports_uses_configured_timezone_for_archive_date(tmp_path, monkeypatch):
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
    monkeypatch.setattr("auto_report.app.datetime", _FrozenAppDateTime)
    monkeypatch.setenv("AUTO_TIMEZONE", "Asia/Shanghai")

    generated_files, _, _ = render_reports(tmp_path)
    payload = json.loads((tmp_path / "data" / "reports" / "latest-summary-auto.json").read_text(encoding="utf-8"))
    normalized_paths = [path.replace("\\", "/") for path in generated_files]

    assert payload["meta"]["generated_at"].startswith("2026-04-13T07:59:54+08:00")
    assert any("data/archives/2026-04-13/" in path for path in normalized_paths)


def test_run_once_persists_status_generated_at_in_configured_timezone(tmp_path, monkeypatch):
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
    monkeypatch.setattr("auto_report.app.datetime", _FrozenAppDateTime)
    monkeypatch.setattr("auto_report.pipeline.run_once.datetime", _FrozenStatusDateTime)
    monkeypatch.setenv("AUTO_TIMEZONE", "Asia/Shanghai")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "false")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))

    assert status["generated_at"].startswith("2026-04-13T07:59:54+08:00")


def test_run_once_skips_push_when_disabled(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.send_feishu_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("push should be skipped")),
    )
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "false")

    run_once(tmp_path)

    status = (tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8")
    assert '"pushed": false' in status
    assert '"stage_status"' in status
    assert '"source_stats"' in status
    assert '"risk_level"' in status
    assert '"ai_metrics"' in status


def test_run_once_records_reviewed_publication_mode_and_detail_link(tmp_path, monkeypatch):
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

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "auto_report.app.collect_all_items",
        lambda settings: (sample_items, ["测试诊断"]),
    )

    def fake_send_feishu_messages(app_id, app_secret, chat_id, text, **kwargs):
        captured["app_id"] = app_id
        captured["chat_id"] = chat_id
        captured["text"] = text
        captured["card"] = kwargs.get("card")
        return [{"code": 0, "msg": "success", "data": {"message_id": "om_1"}, "delivery_kind": "card_success"}]

    monkeypatch.setattr("auto_report.app.send_feishu_messages", fake_send_feishu_messages)
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(
        tmp_path,
        publication_mode="reviewed",
        reviewer="Alice",
        review_note="checked key sources",
    )

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))

    assert status["publication_mode"] == "reviewed"
    assert status["review"]["reviewer"] == "Alice"
    assert status["review"]["review_note"] == "checked key sources"
    assert any(path.endswith("latest-summary-reviewed.md") for path in status["generated_files"])
    assert "https://wsysgz.github.io/VS_AI/" in str(captured["text"])
    assert "latest-summary-reviewed.md" in str(captured["text"])
    assert captured["card"]


def test_run_once_sends_feishu_mid_length_report_when_configured(tmp_path, monkeypatch):
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

    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "auto_report.app.collect_all_items",
        lambda settings: (sample_items, ["测试诊断"]),
    )
    def fake_send_feishu_messages(app_id, app_secret, chat_id, text, **kwargs):
        captured["app_id"] = app_id
        captured["chat_id"] = chat_id
        captured["text"] = text
        return [{"code": 0, "data": {"message_id": "om_1"}}]

    monkeypatch.setattr("auto_report.app.send_feishu_messages", fake_send_feishu_messages)
    monkeypatch.setenv("FEISHU_APP_ID", "feishu-app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "feishu-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "oc_xxx")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert captured["app_id"] == "feishu-app"
    assert captured["chat_id"] == "oc_xxx"
    assert captured["text"].startswith("AI情报飞书简报 |")
    assert "执行摘要" in captured["text"]
    assert "关键主线" in captured["text"]
    assert "行动建议" in captured["text"]
    assert "重点主题" not in captured["text"]
    assert "公开阅读：" in captured["text"]
    assert "GitHub 原文：" in captured["text"]


def test_run_once_ignores_retired_channels_even_when_configured(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pushplus should be retired")),
        raising=False,
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("telegram should be retired")),
        raising=False,
    )
    monkeypatch.setattr("auto_report.app.send_feishu_messages", lambda *args, **kwargs: [{"code": 0, "data": {"message_id": "om_1"}}])
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["push_channel"] == "feishu"
    assert status["delivery_results"]["successful_channels"] == ["feishu"]
    assert set(status["delivery_results"]["channels"]) == {"feishu"}


def test_run_once_records_feishu_sidecar_status_when_enabled(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.sync_feishu_workspace_sidecar",
        lambda *args, **kwargs: {"report_doc": {"doc_token": "doc_1"}},
    )
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_SIDECAR_ENABLED", "true")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    monkeypatch.delenv("FEISHU_CHAT_ID", raising=False)

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["feishu_sidecar"]["enabled"] is True
    assert status["feishu_sidecar"]["ok"] is True
    assert status["feishu_sidecar"]["report_doc"]["doc_token"] == "doc_1"


def test_run_once_skips_feishu_sidecar_in_github_actions(tmp_path, monkeypatch):
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
    def _unexpected_sidecar(*args, **kwargs):
        raise AssertionError("sidecar should not run in GitHub Actions")

    monkeypatch.setattr("auto_report.app.sync_feishu_workspace_sidecar", _unexpected_sidecar)
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_SIDECAR_ENABLED", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    monkeypatch.delenv("FEISHU_CHAT_ID", raising=False)

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["feishu_sidecar"]["enabled"] is False
    assert status["feishu_sidecar"]["ok"] is False
    assert status["feishu_sidecar"]["reason"] == "github_actions"


def test_cmd_sync_feishu_workspace_skips_in_github_actions(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setattr(
        "auto_report.app.sync_feishu_workspace_sidecar",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not run")),
    )

    status = cmd_sync_feishu_workspace(tmp_path, publication_mode="reviewed")

    assert status["enabled"] is False
    assert status["ok"] is False
    assert status["reason"] == "github_actions"


def test_cmd_diagnose_delivery_uses_feishu_only(monkeypatch):
    tmp_path = Path.cwd()

    captured: dict[str, object] = {}

    monkeypatch.setattr("auto_report.app._build_feishu_notification", lambda *args, **kwargs: "feishu text")
    monkeypatch.setattr(
        "auto_report.app._build_feishu_notification_card",
        lambda *args, **kwargs: {"header": {"title": {"content": "card"}}, "elements": []},
    )

    def fake_send_feishu_messages(app_id, app_secret, chat_id, text, **kwargs):
        captured["text"] = text
        captured["card"] = kwargs.get("card")
        return [{"code": 0, "data": {"message_id": "om_1"}, "delivery_kind": "card_success"}]

    monkeypatch.setattr("auto_report.app.send_feishu_messages", fake_send_feishu_messages)
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pushplus should not send")),
        raising=False,
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("telegram should not send")),
        raising=False,
    )
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    summary = cmd_diagnose_delivery(
        tmp_path,
        send=True,
        mode="full-report",
        require_feishu_card_success=True,
    )

    assert captured["text"] == "feishu text"
    assert captured["card"] == {"header": {"title": {"content": "card"}}, "elements": []}
    assert summary["successful_channels"] == ["feishu"]
    assert summary["channels"]["feishu"]["delivery_kind"] == "card_success"
    assert set(summary["channels"]) == {"feishu"}


def test_cmd_diagnose_delivery_rejects_retired_channels(monkeypatch):
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    try:
        cmd_diagnose_delivery(Path.cwd(), send=False, channels="pushplus,telegram")
    except ValueError as exc:
        assert "Unsupported delivery channels: pushplus, telegram" in str(exc)
    else:
        raise AssertionError("retired channels should be rejected")


def test_cmd_diagnose_delivery_fails_when_feishu_falls_back_to_text(monkeypatch):
    tmp_path = Path.cwd()

    monkeypatch.setattr("auto_report.app._build_feishu_notification", lambda *args, **kwargs: "feishu text")
    monkeypatch.setattr(
        "auto_report.app._build_feishu_notification_card",
        lambda *args, **kwargs: {"header": {"title": {"content": "card"}}, "elements": []},
    )
    monkeypatch.setattr(
        "auto_report.app.send_feishu_messages",
        lambda *args, **kwargs: [{"code": 0, "data": {"message_id": "om_1"}, "delivery_kind": "text_fallback"}],
    )
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pushplus should not send")),
        raising=False,
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("telegram should not send")),
        raising=False,
    )
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    summary = cmd_diagnose_delivery(
        tmp_path,
        send=True,
        mode="full-report",
        channels="feishu",
        require_feishu_card_success=True,
    )

    assert summary["successful_channels"] == []
    assert summary["failed_channels"] == ["feishu"]
    assert summary["channels"]["feishu"]["delivery_kind"] == "text_fallback"
    assert summary["channels"]["feishu"]["status"] == "error"
    assert "card_success" in summary["channels"]["feishu"]["detail"]

def test_run_once_marks_pushed_false_when_all_channels_fail(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.send_feishu_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")),
    )
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["pushed"] is False
    assert status["delivery_results"]["failed_channels"] == ["feishu"]
    assert set(status["delivery_results"]["channels"]) == {"feishu"}


def test_run_once_leaves_push_channel_empty_when_feishu_fails(tmp_path, monkeypatch):
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
    monkeypatch.setattr("auto_report.app.send_feishu_messages", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")))
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["push_channel"] == ""
    assert status["delivery_results"]["successful_channels"] == []
    assert status["delivery_results"]["failed_channels"] == ["feishu"]


def test_run_once_persists_scheduler_and_delivery_error_metadata(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.send_feishu_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("request timed out")),
    )
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_TRIGGER_KIND", "compensation")
    monkeypatch.setenv("SCHEDULER_COMPENSATION_RUN", "true")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    feishu = status["delivery_results"]["channels"]["feishu"]

    assert status["scheduler"] == {
        "trigger_kind": "compensation",
        "compensation_run": True,
    }
    assert feishu["error_type"] == "network"
    assert feishu["attempted_at"]
    assert set(status["delivery_results"]["channels"]) == {"feishu"}


def test_run_once_writes_external_enrichment_metrics_into_run_status(tmp_path, monkeypatch):
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
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "false")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))

    assert "external_enrichment" in status
    assert status["external_enrichment"]["enabled"] in {True, False}
    assert "success_rate" in status["external_enrichment"]
    assert status["source_stats"]["report_topics"] >= 0
    assert "provider" in status["ai_metrics"]
    assert "token_usage" in status["ai_metrics"]


def test_cmd_analyze_only_enables_ai_for_openai_provider(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "intermediate.json").write_text(
        json.dumps(
            {
                "candidates": [
                    {
                        "topic_id": "topic-1",
                        "title": "Topic 1",
                        "url": "https://example.com/1",
                        "primary_domain": "ai-llm-agent",
                        "matched_domains": ["ai-llm-agent"],
                        "evidence_count": 1,
                        "source_ids": ["rss"],
                        "tags": ["agent"],
                        "evidence_snippets": ["Snippet 1"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    def fake_run_staged_ai_pipeline(**kwargs):
        captured.update(kwargs)
        return {
            "analyses": [],
            "summary": {},
            "forecast": {},
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
        }

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.run_staged_ai_pipeline",
        fake_run_staged_ai_pipeline,
    )
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    cmd_analyze_only(tmp_path)

    assert captured["ai_enabled"] is True
