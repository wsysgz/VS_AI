import json
import shutil
from pathlib import Path

from auto_report.app import run_once
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


def test_build_run_status_includes_stage_status_and_source_counts():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        stage_status={"analysis": "ok", "summary": "fallback", "forecast": "fallback"},
        source_stats={"collected_items": 12, "filtered_topics": 5},
    )

    assert status["stage_status"]["analysis"] == "ok"
    assert status["source_stats"]["filtered_topics"] == 5


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


def test_build_run_status_includes_delivery_results():
    delivery_results = {
        "successful_channels": ["pushplus"],
        "failed_channels": ["telegram"],
        "skipped_channels": ["feishu"],
    }

    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=True,
        delivery_results=delivery_results,
    )

    assert status["delivery_results"] == delivery_results


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

    generated_files, _ = render_reports(tmp_path)

    assert any(path.endswith("latest-summary.md") for path in generated_files)
    content = (tmp_path / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8")
    assert "自动情报快报" in content
    assert "## 一句话判断" in content
    assert "## 重点主线" in content
    assert "## 行动建议" in content


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

    assert captured["channel"] == "clawbot"
    assert captured["template"] == "txt"
    assert "今日判断：" in captured["content"]
    assert "三条主线：" in captured["content"]
    assert "详情链接：" in captured["content"]
    assert "https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md" in captured["content"]


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
    assert "详情链接：" in captured["text"]


def test_run_once_marks_pushed_false_when_all_channels_fail(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: ([], []))
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pushplus down")))
    monkeypatch.setattr("auto_report.app.send_telegram_messages", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("telegram down")))
    monkeypatch.setattr("auto_report.app.send_feishu_messages", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")))
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
    assert status["delivery_results"]["failed_channels"] == ["pushplus", "telegram", "feishu"]


def test_run_once_marks_only_successful_channels_in_push_channel(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: ([], []))
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})
    monkeypatch.setattr("auto_report.app.send_telegram_messages", lambda *args, **kwargs: [{"ok": True, "result": {"message_id": 1}}])
    monkeypatch.setattr("auto_report.app.send_feishu_messages", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("feishu down")))
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert status["push_channel"] == "pushplus,telegram"


def test_run_once_passes_delivery_endpoint_settings_to_senders(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    captured: dict[str, object] = {}

    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: ([], []))

    def fake_send_pushplus(token, title, content, channel="", template="markdown", secret_key="", **kwargs):
        captured["pushplus"] = kwargs
        return {"code": 200}

    def fake_send_telegram_messages(token, chat_id, text, **kwargs):
        captured["telegram"] = kwargs
        return [{"ok": True, "result": {"message_id": 1}}]

    def fake_send_feishu_messages(app_id, app_secret, receive_id, text, **kwargs):
        captured["feishu"] = kwargs
        return [{"code": 0, "msg": "success"}]

    monkeypatch.setattr("auto_report.app.send_pushplus", fake_send_pushplus)
    monkeypatch.setattr("auto_report.app.send_telegram_messages", fake_send_telegram_messages)
    monkeypatch.setattr("auto_report.app.send_feishu_messages", fake_send_feishu_messages)
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_BASE_URL", "https://pushplus-proxy.example")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat-id")
    monkeypatch.setenv("TELEGRAM_API_BASE_URL", "https://telegram-proxy.example")
    monkeypatch.setenv("FEISHU_APP_ID", "app-id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "app-secret")
    monkeypatch.setenv("FEISHU_CHAT_ID", "chat-id")
    monkeypatch.setenv("FEISHU_API_BASE_URL", "https://feishu-proxy.example")
    monkeypatch.setenv("DELIVERY_REQUEST_TIMEOUT", "33")

    run_once(tmp_path)

    assert captured["pushplus"] == {"base_url": "https://pushplus-proxy.example", "timeout": 33}
    assert captured["telegram"] == {"api_base_url": "https://telegram-proxy.example", "timeout": 33}
    assert captured["feishu"] == {"api_base_url": "https://feishu-proxy.example", "timeout": 33}
