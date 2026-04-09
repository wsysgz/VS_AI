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

    def fake_send_pushplus(token, title, content, channel="", template="markdown"):
        captured["channel"] = channel
        captured["template"] = template
        captured["content"] = content
        return {"code": 200}

    monkeypatch.setattr("auto_report.app.send_pushplus", fake_send_pushplus)
    monkeypatch.setenv("PUSHPLUS_TOKEN", "token")
    monkeypatch.setenv("PUSHPLUS_CHANNEL", "clawbot")
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "true")

    run_once(tmp_path)

    assert captured["channel"] == "clawbot"
    assert captured["template"] == "txt"
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

    def fake_send_telegram_messages(token, chat_id, text):
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
    assert captured["text"].startswith("# 自动情报快报")
    assert "## 核心看点" in captured["text"]
    assert "详情链接：" in captured["text"]
