from pathlib import Path

from auto_report.settings import load_settings


def test_load_settings_reads_domains_and_sources():
    settings = load_settings(Path.cwd())
    assert settings.providers["llm"]["provider"] == "deepseek"
    assert len(settings.domains) == 2
    assert "rss" in settings.sources


def test_load_settings_includes_morning_schedule_and_push_channel_defaults(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    settings = load_settings(Path.cwd())
    assert settings.schedules["jobs"]["daily"]["cron"] == "0 23 * * *"
    assert settings.env["PUSHPLUS_CHANNEL"] == "clawbot"
    assert settings.env["REPORT_REPO_URL"] == "https://github.com/wsysgz/VS_AI"
    assert "TELEGRAM_BOT_TOKEN" in settings.env
    assert "TELEGRAM_CHAT_ID" in settings.env


def test_load_settings_exposes_ai_reading_paths():
    settings = load_settings(Path.cwd())
    assert settings.ai_reading["analysis"].name == "analysis-before.md"
    assert settings.ai_reading["summary"].name == "summary-before.md"
    assert settings.ai_reading["forecast"].name == "forecast-before.md"
