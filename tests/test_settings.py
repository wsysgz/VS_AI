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
    assert settings.schedules["jobs"]["daily"]["cron"] == "13 23 * * *"
    assert settings.env["PUSHPLUS_CHANNEL"] == "clawbot"
    assert settings.env["REPORT_REPO_URL"] == "https://github.com/wsysgz/VS_AI"
    assert "TELEGRAM_BOT_TOKEN" in settings.env
    assert "TELEGRAM_CHAT_ID" in settings.env


def test_load_settings_exposes_scheduler_defaults():
    settings = load_settings(Path.cwd())

    assert settings.env["SCHEDULER_TRIGGER_KIND"] == "manual"
    assert settings.env["SCHEDULER_COMPENSATION_RUN"] == "false"
    assert settings.env["PUBLICATION_MODE"] == "auto"
    assert settings.env["EXTERNAL_ENRICHMENT_ENABLED"] == "false"
    assert settings.env["EXTERNAL_ENRICHMENT_MAX_SIGNALS"] == "2"
    assert settings.env["EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS"] == "8"


def test_load_settings_allows_publication_mode_override(monkeypatch):
    monkeypatch.setenv("PUBLICATION_MODE", "reviewed")

    settings = load_settings(Path.cwd())

    assert settings.env["PUBLICATION_MODE"] == "reviewed"


def test_load_settings_exposes_ai_reading_paths():
    settings = load_settings(Path.cwd())
    assert settings.ai_reading["analysis"].name == "analysis-before.md"
    assert settings.ai_reading["summary"].name == "summary-before.md"
    assert settings.ai_reading["forecast"].name == "forecast-before.md"
    assert settings.env["AI_MAX_ANALYSIS_TOPICS"] == "6"


def test_load_settings_includes_delivery_endpoint_defaults():
    settings = load_settings(Path.cwd())
    assert settings.env["PUSHPLUS_BASE_URL"] == "https://www.pushplus.plus"
    assert settings.env["TELEGRAM_API_BASE_URL"] == "https://api.telegram.org"
    assert settings.env["FEISHU_API_BASE_URL"] == "https://open.feishu.cn"
    assert settings.env["DELIVERY_REQUEST_TIMEOUT"] == "20"


def test_load_settings_uses_curated_live_website_entry_points():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }

    assert website_sources["deepseek-updates"]["url"] == "https://api-docs.deepseek.com/updates/"
    assert website_sources["moonshot-blog"]["url"] == "https://platform.moonshot.cn/blog"
    assert website_sources["deepseek-updates"]["mode"] == "structured_page"
    assert website_sources["moonshot-blog"]["mode"] == "structured_page"
    assert website_sources["qwen-blog"]["url"] == "https://qwen.ai/research#research_latest_advancements"
    assert website_sources["qwen-blog"]["api_url"] == "https://qwen.ai/api/v2/article/retrieval?type=qwen_ai&language=zh-CN"
    assert website_sources["qwen-blog"]["mode"] == "json_api"
    assert website_sources["openvino-blog"]["mode"] == "structured_page"


def test_load_settings_includes_edge_infra_source_pack():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }

    assert "nvidia-embedded" in website_sources
    assert "openvino-blog" in website_sources
    assert "nxp-edge-ai" in website_sources
    assert "google-ai-edge" in rss_sources


def test_load_settings_uses_live_curated_chip_ai_repositories():
    settings = load_settings(Path.cwd())
    github_sources = {
        source["id"]: source for source in settings.sources["github"]["sources"]
    }

    repos = github_sources["curated-chip-ai-repos"]["repositories"]

    assert "NVIDIA/TensorRT" in repos
    assert "NVIDIA/cuda-cmake" not in repos


def test_load_settings_disables_dead_vendor_ai_blog_slots():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }

    assert website_sources["st-blog"]["enabled"] is False
    assert website_sources["ti-e2e-blog"]["enabled"] is False


def test_load_settings_uses_live_arxiv_atom_entry_point():
    settings = load_settings(Path.cwd())
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }

    assert rss_sources["arxiv-cs-ai"]["url"].startswith("https://export.arxiv.org/api/query?")
    assert rss_sources["google-ai-edge"]["url"] == "https://blog.google/innovation-and-ai/technology/ai/rss/"


def test_load_settings_includes_youtube_v0_official_channel_feeds():
    settings = load_settings(Path.cwd())
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }

    assert rss_sources["youtube-google-developers"]["url"] == "https://www.youtube.com/feeds/videos.xml?user=GoogleDevelopers"
    assert rss_sources["youtube-google-developers"]["category_hint"] == "ai-x-electronics"
    assert rss_sources["youtube-google-developers"]["timeout_seconds"] == 8
    assert rss_sources["youtube-nvidia"]["url"] == "https://www.youtube.com/feeds/videos.xml?user=nvidia"
    assert rss_sources["youtube-nvidia"]["category_hint"] == "ai-x-electronics"
    assert rss_sources["youtube-nvidia"]["timeout_seconds"] == 8
    assert "youtube-microsoft-developer" not in rss_sources
    assert "youtube-pytorch" not in rss_sources


def test_load_settings_exposes_p1_source_registry_metadata():
    settings = load_settings(Path.cwd())
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }

    assert rss_sources["meta-ai-blog"]["stability_tier"] == "manual-watch"
    assert rss_sources["meta-ai-blog"]["replacement_hint"] == "Confirm a live Meta AI feed or disable this slot"
    assert rss_sources["meta-ai-blog"]["watch_strategy"] == "manual-review"
    assert rss_sources["meta-ai-blog"]["replacement_target"] == "official-meta-feed"
    assert website_sources["st-blog"]["stability_tier"] == "manual-watch"
    assert website_sources["st-blog"]["replacement_hint"] == "Replace with a stable ST AI listing or RSSHub route"
    assert website_sources["st-blog"]["watch_strategy"] == "manual-review"
    assert website_sources["st-blog"]["replacement_target"] == "rsshub-or-stable-listing"
