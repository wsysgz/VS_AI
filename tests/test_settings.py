from pathlib import Path

from auto_report.settings import load_settings


def test_load_settings_reads_domains_and_sources():
    settings = load_settings(Path.cwd())
    assert settings.providers["llm"]["provider"] == "deepseek"
    assert len(settings.domains) == 2
    assert "rss" in settings.sources
