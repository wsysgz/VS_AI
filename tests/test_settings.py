import shutil
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


def test_load_settings_includes_stage_level_ai_env(monkeypatch):
    monkeypatch.setenv("ANALYSIS_AI_PROVIDER", "deepseek")
    monkeypatch.setenv("ANALYSIS_AI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("ANALYSIS_AI_MODEL", "deepseek-chat")
    monkeypatch.setenv("SUMMARY_AI_PROVIDER", "minimax_svips")
    monkeypatch.setenv("SUMMARY_AI_BASE_URL", "https://api.svips.org/v1")
    monkeypatch.setenv("SUMMARY_AI_MODEL", "MiniMax-M2.7")
    monkeypatch.setenv("FORECAST_AI_PROVIDER", "deepseek")
    monkeypatch.setenv("FORECAST_AI_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("FORECAST_AI_MODEL", "deepseek-chat")

    settings = load_settings(Path.cwd())

    assert settings.env["ANALYSIS_AI_PROVIDER"] == "deepseek"
    assert settings.env["ANALYSIS_AI_BASE_URL"] == "https://api.deepseek.com"
    assert settings.env["ANALYSIS_AI_MODEL"] == "deepseek-chat"
    assert settings.env["SUMMARY_AI_PROVIDER"] == "minimax_svips"
    assert settings.env["SUMMARY_AI_BASE_URL"] == "https://api.svips.org/v1"
    assert settings.env["SUMMARY_AI_MODEL"] == "MiniMax-M2.7"
    assert settings.env["FORECAST_AI_PROVIDER"] == "deepseek"
    assert settings.env["FORECAST_AI_BASE_URL"] == "https://api.deepseek.com"
    assert settings.env["FORECAST_AI_MODEL"] == "deepseek-chat"


def test_load_settings_includes_helper_stage_ai_env(monkeypatch):
    monkeypatch.setenv("PREFILTER_AI_PROVIDER", "minimax_svips")
    monkeypatch.setenv("PREFILTER_AI_BASE_URL", "https://api.svips.org/v1")
    monkeypatch.setenv("PREFILTER_AI_MODEL", "MiniMax-M2.7")
    monkeypatch.setenv("DISCOVERY_AI_PROVIDER", "minimax_svips")
    monkeypatch.setenv("DISCOVERY_AI_BASE_URL", "https://api.svips.org/v1")
    monkeypatch.setenv("DISCOVERY_AI_MODEL", "MiniMax-M2.7")
    monkeypatch.setenv("SEARCH_AI_PROVIDER", "minimax_svips")
    monkeypatch.setenv("SEARCH_AI_BASE_URL", "https://api.svips.org/v1")
    monkeypatch.setenv("SEARCH_AI_MODEL", "MiniMax-M2.7")

    settings = load_settings(Path.cwd())

    assert settings.env["PREFILTER_AI_PROVIDER"] == "minimax_svips"
    assert settings.env["PREFILTER_AI_BASE_URL"] == "https://api.svips.org/v1"
    assert settings.env["PREFILTER_AI_MODEL"] == "MiniMax-M2.7"
    assert settings.env["DISCOVERY_AI_PROVIDER"] == "minimax_svips"
    assert settings.env["DISCOVERY_AI_BASE_URL"] == "https://api.svips.org/v1"
    assert settings.env["DISCOVERY_AI_MODEL"] == "MiniMax-M2.7"
    assert settings.env["SEARCH_AI_PROVIDER"] == "minimax_svips"
    assert settings.env["SEARCH_AI_BASE_URL"] == "https://api.svips.org/v1"
    assert settings.env["SEARCH_AI_MODEL"] == "MiniMax-M2.7"


def test_load_settings_includes_litellm_gateway_env(monkeypatch):
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-litellm")

    settings = load_settings(Path.cwd())

    assert settings.env["LITELLM_MASTER_KEY"] == "sk-litellm"


def test_load_settings_includes_langfuse_env(monkeypatch):
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_ENV", "local")
    monkeypatch.setenv("LANGFUSE_CAPTURE_CONTENT", "false")

    settings = load_settings(Path.cwd())

    assert settings.env["LANGFUSE_ENABLED"] == "true"
    assert settings.env["LANGFUSE_PUBLIC_KEY"] == "pk-lf-test"
    assert settings.env["LANGFUSE_SECRET_KEY"] == "sk-lf-test"
    assert settings.env["LANGFUSE_BASE_URL"] == "https://cloud.langfuse.com"
    assert settings.env["LANGFUSE_ENV"] == "local"
    assert settings.env["LANGFUSE_CAPTURE_CONTENT"] == "false"


def test_load_settings_includes_backup_provider_and_budget_env(monkeypatch):
    monkeypatch.setenv("BACKUP_AI_PROVIDER", "openai")
    monkeypatch.setenv("BACKUP_AI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("BACKUP_AI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("BACKUP_AI_API_KEY", "backup-key")
    monkeypatch.setenv("AI_MAX_STAGE_LATENCY_SECONDS", "12.5")
    monkeypatch.setenv("AI_MAX_STAGE_TOTAL_TOKENS", "5000")
    monkeypatch.setenv("SUMMARY_BACKUP_AI_PROVIDER", "litellm_proxy")
    monkeypatch.setenv("SUMMARY_BACKUP_AI_MODEL", "vs-ai-summary-backup")
    monkeypatch.setenv("SUMMARY_BACKUP_AI_API_KEY", "summary-backup-key")
    monkeypatch.setenv("SUMMARY_AI_MAX_LATENCY_SECONDS", "9.0")
    monkeypatch.setenv("SUMMARY_AI_MAX_TOTAL_TOKENS", "2500")

    settings = load_settings(Path.cwd())

    assert settings.env["BACKUP_AI_PROVIDER"] == "openai"
    assert settings.env["BACKUP_AI_BASE_URL"] == "https://api.openai.com/v1"
    assert settings.env["BACKUP_AI_MODEL"] == "gpt-4o-mini"
    assert settings.env["BACKUP_AI_API_KEY"] == "backup-key"
    assert settings.env["AI_MAX_STAGE_LATENCY_SECONDS"] == "12.5"
    assert settings.env["AI_MAX_STAGE_TOTAL_TOKENS"] == "5000"
    assert settings.env["SUMMARY_BACKUP_AI_PROVIDER"] == "litellm_proxy"
    assert settings.env["SUMMARY_BACKUP_AI_MODEL"] == "vs-ai-summary-backup"
    assert settings.env["SUMMARY_BACKUP_AI_API_KEY"] == "summary-backup-key"
    assert settings.env["SUMMARY_AI_MAX_LATENCY_SECONDS"] == "9.0"
    assert settings.env["SUMMARY_AI_MAX_TOTAL_TOKENS"] == "2500"


def test_load_settings_includes_delivery_endpoint_defaults(tmp_path, monkeypatch):
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.delenv("FEISHU_SIDECAR_ENABLED", raising=False)
    monkeypatch.delenv("FEISHU_DOC_WIKI_SPACE", raising=False)
    monkeypatch.delenv("FEISHU_GOVERNANCE_TASK_LIMIT", raising=False)
    monkeypatch.delenv("LARK_CLI_PATH", raising=False)
    monkeypatch.delenv("LARK_CLI_PROFILE", raising=False)
    settings = load_settings(tmp_path)
    assert settings.env["PUSHPLUS_BASE_URL"] == "https://www.pushplus.plus"
    assert settings.env["TELEGRAM_API_BASE_URL"] == "https://api.telegram.org"
    assert settings.env["FEISHU_API_BASE_URL"] == "https://open.feishu.cn"
    assert settings.env["DELIVERY_REQUEST_TIMEOUT"] == "20"
    assert settings.env["LARK_CLI_PATH"] == "D:\\AI\\Feishu\\feushu_cli\\lark-cli.exe"
    assert settings.env["LARK_CLI_PROFILE"] == "vs_ai"
    assert settings.env["FEISHU_SIDECAR_ENABLED"] == "false"


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


def test_load_settings_marks_anthropic_news_as_validated_listing():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }

    anthropic = website_sources["anthropic-news"]
    assert anthropic["mode"] == "article_listing"
    assert anthropic["url"] == "https://www.anthropic.com/news"
    assert anthropic["stability_tier"] == "verified-listing"
    assert anthropic["watch_strategy"] == "listing-poll"
    assert anthropic["candidate_kind"] == "validated_listing"
    assert anthropic["candidate_value"] == "https://www.anthropic.com/news"


def test_load_settings_includes_edge_infra_source_pack():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }
    github_sources = {
        source["id"]: source for source in settings.sources["github"]["sources"]
    }
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }

    assert "openvino-blog" in website_sources
    assert "nxp-edge-ai" in website_sources
    assert "arm-news" in rss_sources
    assert "nvidia-embedded" in rss_sources
    assert "google-ai-edge" in rss_sources
    assert "ti-e2e-blog" in website_sources
    assert "st-blog" in rss_sources
    assert "dm-eiq-genai-flow-demonstrator" in " ".join(github_sources["curated-edge-repos"]["repositories"])


def test_load_settings_uses_live_curated_chip_ai_repositories():
    settings = load_settings(Path.cwd())
    github_sources = {
        source["id"]: source for source in settings.sources["github"]["sources"]
    }

    repos = github_sources["curated-chip-ai-repos"]["repositories"]

    assert "NVIDIA/TensorRT" in repos
    assert "NVIDIA/cuda-cmake" not in repos


def test_load_settings_includes_recent_domestic_and_international_governance_sources():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }
    github_sources = {
        source["id"]: source for source in settings.sources["github"]["sources"]
    }

    assert "zhipu-news" in website_sources
    assert website_sources["zhipu-news"]["url"] == "https://www.zhipuai.cn/zh/news"
    assert "renesas-blog" in website_sources
    assert "edge-impulse-blog" in website_sources
    assert "cerebras-blog" in website_sources
    assert website_sources["cerebras-blog"]["url"] == "https://www.cerebras.ai/blog"
    assert website_sources["cerebras-blog"]["mode"] == "article_listing"
    assert "groq-blog" in website_sources
    assert website_sources["groq-blog"]["url"] == "https://groq.com/blog"
    assert website_sources["groq-blog"]["mode"] == "structured_page"
    assert "espressif-blog" in website_sources
    assert website_sources["espressif-blog"]["url"] == "https://developer.espressif.com/blog/"
    assert "mediatek-blog" in website_sources
    assert website_sources["mediatek-blog"]["url"] == "https://www.mediatek.com/blog"
    assert website_sources["infineon-blog"]["mode"] == "json_api"
    assert "insightsarticlenewsl.pagelisting.json" in website_sources["infineon-blog"]["api_url"]
    assert website_sources["qualcomm-onq"]["mode"] == "json_api"
    assert website_sources["qualcomm-onq"]["api_method"] == "post"

    agent_repos = github_sources["curated-agent-repos"]["repositories"]
    infra_repos = github_sources["curated-infra-repos"]["repositories"]
    edge_repos = github_sources["curated-edge-repos"]["repositories"]

    assert "microsoft/autogen" in agent_repos
    assert "openai/openai-agents-python" in agent_repos
    assert "mistralai/mistral-inference" in infra_repos
    assert "QwenLM/Qwen3" in agent_repos
    assert "modelscope/ms-swift" in infra_repos
    assert "deepseek-ai/DeepEP" in infra_repos
    assert "espressif/esp-dl" in edge_repos
    assert "Seeed-Studio/SSCMA-Micro" in edge_repos


def test_load_settings_disables_dead_vendor_ai_blog_slots():
    settings = load_settings(Path.cwd())
    website_sources = {
        source["id"]: source for source in settings.sources["websites"]["sources"]
    }
    rss_sources = {
        source["id"]: source for source in settings.sources["rss"]["sources"]
    }

    assert rss_sources["st-blog"]["enabled"] is True
    assert website_sources["ti-e2e-blog"]["enabled"] is True


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

    assert rss_sources["youtube-google-developers"]["url"] == "https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw"
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

    assert rss_sources["meta-ai-blog"]["stability_tier"] == "stable-feed"
    assert rss_sources["meta-ai-blog"]["replacement_hint"] == ""
    assert rss_sources["meta-ai-blog"]["watch_strategy"] == "feed-poll"
    assert rss_sources["meta-ai-blog"]["replacement_target"] == "none"
    assert rss_sources["st-blog"]["stability_tier"] == "stable-feed"
    assert rss_sources["st-blog"]["replacement_hint"] == ""
    assert rss_sources["st-blog"]["watch_strategy"] == "feed-poll"
    assert rss_sources["st-blog"]["replacement_target"] == "none"
    assert website_sources["ti-e2e-blog"]["mode"] == "json_api"
    assert website_sources["nxp-edge-ai"]["enabled"] is False
    assert website_sources["nxp-edge-ai"]["replacement_target"] == "nxp-appcodehub/dm-eiq-genai-flow-demonstrator"
