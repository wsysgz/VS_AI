import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from auto_report.app import cmd_analyze_only, cmd_sync_feishu_workspace, run_once
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


def test_build_run_status_summarizes_push_responses():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        push_channel="clawbot",
        push_response={
            "pushplus": {
                "code": 200,
                "msg": "执行成功",
                "data": "pushplus-id",
                "extra": "should-not-be-copied",
            },
            "telegram": [
                {
                    "ok": True,
                    "result": {
                        "message_id": 7,
                        "text": "# 自动情报快报",
                        "chat": {"id": 8566057843, "username": "wsysgz"},
                    },
                },
                {
                    "ok": True,
                    "result": {
                        "message_id": 8,
                        "text": "详情链接",
                        "chat": {"id": 8566057843, "username": "wsysgz"},
                    },
                },
            ],
        },
    )

    assert status["push_response"]["pushplus"] == {
        "code": 200,
        "msg": "执行成功",
        "data": "pushplus-id",
    }
    assert status["push_response"]["telegram"] == {
        "ok": True,
        "messages_sent": 2,
        "message_ids": [7, 8],
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
        "auto_report.app.send_pushplus",
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

    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "auto_report.app.collect_all_items",
        lambda settings: (sample_items, ["测试诊断"]),
    )

    def fake_send_pushplus(token, title, content, channel="", template="markdown", secret_key="", **kwargs):
        captured["title"] = title
        captured["content"] = content
        return {"code": 200}

    monkeypatch.setattr("auto_report.app.send_pushplus", fake_send_pushplus)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
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
    assert "https://wsysgz.github.io/VS_AI/" in captured["content"]
    assert "latest-summary-reviewed.md" in captured["content"]


def test_run_once_uses_configured_pushplus_channel(tmp_path, monkeypatch):
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

    def fake_send_pushplus(token, title, content, channel="", template="markdown", secret_key="", **kwargs):
        captured["channel"] = channel
        captured["template"] = template
        captured["content"] = content
        return {"code": 200}

    monkeypatch.setattr("auto_report.app.send_pushplus", fake_send_pushplus)
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("telegram should be skipped")),
    )
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert captured["content"].startswith("AI情报早报 |")
    assert captured["channel"] == "clawbot"
    assert captured["template"] == "txt"
    assert "今日判断：" in captured["content"]
    assert "三条主线：" in captured["content"]
    assert "公开阅读：" in captured["content"]
    assert "GitHub 原文：" in captured["content"]
    assert "https://wsysgz.github.io/VS_AI/" in captured["content"]
    assert "https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary-auto.md" in captured["content"]
    assert "执行摘要" not in captured["content"]


def test_run_once_sends_full_telegram_report_when_configured(tmp_path, monkeypatch):
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
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: {"code": 200},
    )

    def fake_send_telegram_messages(token, chat_id, text, **kwargs):
        captured["token"] = token
        captured["chat_id"] = chat_id
        captured["text"] = text
        return [{"ok": True}]

    monkeypatch.setattr("auto_report.app.send_telegram_messages", fake_send_telegram_messages)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "8566057843")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert captured["token"] == "telegram-token"
    assert captured["chat_id"] == "8566057843"
    assert captured["text"].startswith("AI情报完整简报 |")
    assert "执行摘要" in captured["text"]
    assert "关键主线" in captured["text"]
    assert "重点主题" in captured["text"]
    assert "公开阅读：" in captured["text"]
    assert "GitHub 原文：" in captured["text"]


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
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: {"code": 200},
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: [{"ok": True, "result": {"message_id": 1}}],
    )

    def fake_send_feishu_messages(app_id, app_secret, chat_id, text, **kwargs):
        captured["app_id"] = app_id
        captured["chat_id"] = chat_id
        captured["text"] = text
        return [{"code": 0, "data": {"message_id": "om_1"}}]

    monkeypatch.setattr("auto_report.app.send_feishu_messages", fake_send_feishu_messages)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "8566057843")
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


def test_run_once_prefers_feishu_as_primary_delivery_channel(tmp_path, monkeypatch):
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
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})
    monkeypatch.setattr("auto_report.app.send_telegram_messages", lambda *args, **kwargs: [{"ok": True, "result": {"message_id": 1}}])
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
    assert status["push_channel"] == "feishu,pushplus,telegram"
    assert status["delivery_results"]["successful_channels"] == ["feishu", "pushplus", "telegram"]


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
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})
    monkeypatch.setattr(
        "auto_report.app.sync_feishu_workspace_sidecar",
        lambda *args, **kwargs: {"report_doc": {"doc_token": "doc_1"}},
    )
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_SIDECAR_ENABLED", "true")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
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
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})

    def _unexpected_sidecar(*args, **kwargs):
        raise AssertionError("sidecar should not run in GitHub Actions")

    monkeypatch.setattr("auto_report.app.sync_feishu_workspace_sidecar", _unexpected_sidecar)
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("FEISHU_SIDECAR_ENABLED", "true")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
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
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pushplus down")),
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("telegram down")),
    )
    monkeypatch.setattr(
        "auto_report.app.send_feishu_messages",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")),
    )
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["pushed"] is False
    assert status["delivery_results"]["failed_channels"] == ["feishu", "pushplus", "telegram"]


def test_run_once_marks_only_successful_channels_in_push_channel(tmp_path, monkeypatch):
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
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})
    monkeypatch.setattr("auto_report.app.send_telegram_messages", lambda *args, **kwargs: [{"ok": True, "result": {"message_id": 1}}])
    monkeypatch.setattr("auto_report.app.send_feishu_messages", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")))
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
    assert status["push_channel"] == "pushplus,telegram"
    assert status["delivery_results"]["successful_channels"] == ["pushplus", "telegram"]
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
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("request timed out")),
    )
    monkeypatch.setattr(
        "auto_report.app.send_telegram_messages",
        lambda *args, **kwargs: [{"ok": True, "result": {"message_id": 1}}],
    )
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    monkeypatch.delenv("FEISHU_CHAT_ID", raising=False)
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("SCHEDULER_TRIGGER_KIND", "compensation")
    monkeypatch.setenv("SCHEDULER_COMPENSATION_RUN", "true")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    pushplus = status["delivery_results"]["channels"]["pushplus"]

    assert status["scheduler"] == {
        "trigger_kind": "compensation",
        "compensation_run": True,
    }
    assert pushplus["error_type"] == "network"
    assert pushplus["attempted_at"]
    assert status["delivery_results"]["channels"]["telegram"]["attempted_at"]


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
    monkeypatch.setattr(
        "auto_report.app.send_pushplus",
        lambda *args, **kwargs: {"code": 200},
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
