from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from dotenv import load_dotenv
import yaml


@dataclass(slots=True)
class Settings:
    root_dir: Path
    providers: dict[str, Any]
    domains: dict[str, dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    schedules: dict[str, Any]
    env: dict[str, str] = field(default_factory=dict)
    ai_reading: dict[str, Path] = field(default_factory=dict)

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_settings(root_dir: Path | None = None) -> Settings:
    resolved_root = (root_dir or Path.cwd()).resolve()
    load_dotenv(resolved_root / ".env", override=False)

    config_dir = resolved_root / "config"
    domains_dir = config_dir / "domains"
    sources_dir = config_dir / "sources"

    domains = {
        path.stem: _read_yaml(path)
        for path in sorted(domains_dir.glob("*.yaml"))
    }
    sources = {
        path.stem: _read_yaml(path)
        for path in sorted(sources_dir.glob("*.yaml"))
    }
    ai_reading = {
        "analysis": config_dir / "ai_reading" / "analysis-before.md",
        "summary": config_dir / "ai_reading" / "summary-before.md",
        "forecast": config_dir / "ai_reading" / "forecast-before.md",
    }

    env = {
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "AI_PROVIDER": os.environ.get("AI_PROVIDER", "deepseek"),
        "AI_BASE_URL": os.environ.get("AI_BASE_URL", "https://api.deepseek.com"),
        "AI_MODEL": os.environ.get("AI_MODEL", "deepseek-chat"),
        "ANALYSIS_AI_PROVIDER": os.environ.get("ANALYSIS_AI_PROVIDER", ""),
        "ANALYSIS_AI_BASE_URL": os.environ.get("ANALYSIS_AI_BASE_URL", ""),
        "ANALYSIS_AI_MODEL": os.environ.get("ANALYSIS_AI_MODEL", ""),
        "SUMMARY_AI_PROVIDER": os.environ.get("SUMMARY_AI_PROVIDER", ""),
        "SUMMARY_AI_BASE_URL": os.environ.get("SUMMARY_AI_BASE_URL", ""),
        "SUMMARY_AI_MODEL": os.environ.get("SUMMARY_AI_MODEL", ""),
        "FORECAST_AI_PROVIDER": os.environ.get("FORECAST_AI_PROVIDER", ""),
        "FORECAST_AI_BASE_URL": os.environ.get("FORECAST_AI_BASE_URL", ""),
        "FORECAST_AI_MODEL": os.environ.get("FORECAST_AI_MODEL", ""),
        "PREFILTER_AI_PROVIDER": os.environ.get("PREFILTER_AI_PROVIDER", ""),
        "PREFILTER_AI_BASE_URL": os.environ.get("PREFILTER_AI_BASE_URL", ""),
        "PREFILTER_AI_MODEL": os.environ.get("PREFILTER_AI_MODEL", ""),
        "DISCOVERY_AI_PROVIDER": os.environ.get("DISCOVERY_AI_PROVIDER", ""),
        "DISCOVERY_AI_BASE_URL": os.environ.get("DISCOVERY_AI_BASE_URL", ""),
        "DISCOVERY_AI_MODEL": os.environ.get("DISCOVERY_AI_MODEL", ""),
        "SEARCH_AI_PROVIDER": os.environ.get("SEARCH_AI_PROVIDER", ""),
        "SEARCH_AI_BASE_URL": os.environ.get("SEARCH_AI_BASE_URL", ""),
        "SEARCH_AI_MODEL": os.environ.get("SEARCH_AI_MODEL", ""),
        "AI_MAX_ANALYSIS_TOPICS": os.environ.get("AI_MAX_ANALYSIS_TOPICS", "6"),
        "PUSHPLUS_TOKEN": os.environ.get("PUSHPLUS_TOKEN", ""),
        "PUSHPLUS_BASE_URL": os.environ.get("PUSHPLUS_BASE_URL", "https://www.pushplus.plus"),
        "PUSHPLUS_SECRETKEY": os.environ.get("PUSHPLUS_SECRETKEY", ""),
        "PUSHPLUS_CHANNEL": os.environ.get("PUSHPLUS_CHANNEL", "clawbot"),
        "PUSHPLUS_FALLBACK_CHANNEL": os.environ.get("PUSHPLUS_FALLBACK_CHANNEL", ""),
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_API_BASE_URL": os.environ.get("TELEGRAM_API_BASE_URL", "https://api.telegram.org"),
        "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
        "FEISHU_APP_ID": os.environ.get("FEISHU_APP_ID", ""),
        "FEISHU_APP_SECRET": os.environ.get("FEISHU_APP_SECRET", ""),
        "FEISHU_API_BASE_URL": os.environ.get("FEISHU_API_BASE_URL", "https://open.feishu.cn"),
        "FEISHU_CHAT_ID": os.environ.get("FEISHU_CHAT_ID", ""),
        "DELIVERY_REQUEST_TIMEOUT": os.environ.get("DELIVERY_REQUEST_TIMEOUT", "20"),
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        "REPORT_REPO_URL": os.environ.get("REPORT_REPO_URL", "https://github.com/wsysgz/VS_AI"),
        "AUTO_TIMEZONE": os.environ.get("AUTO_TIMEZONE", "Asia/Shanghai"),
        "AUTO_PUSH_ENABLED": os.environ.get("AUTO_PUSH_ENABLED", "true"),
        "AUTO_ARCHIVE_TO_GITHUB": os.environ.get("AUTO_ARCHIVE_TO_GITHUB", "true"),
        "PUBLICATION_MODE": os.environ.get("PUBLICATION_MODE", "auto"),
        "SCHEDULER_TRIGGER_KIND": os.environ.get("SCHEDULER_TRIGGER_KIND", "manual"),
        "SCHEDULER_COMPENSATION_RUN": os.environ.get("SCHEDULER_COMPENSATION_RUN", "false"),
        "EXTERNAL_ENRICHMENT_ENABLED": os.environ.get("EXTERNAL_ENRICHMENT_ENABLED", "false"),
        "EXTERNAL_ENRICHMENT_MAX_SIGNALS": os.environ.get("EXTERNAL_ENRICHMENT_MAX_SIGNALS", "2"),
        "EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS": os.environ.get("EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS", "8"),
    }

    return Settings(
        root_dir=resolved_root,
        providers=_read_yaml(config_dir / "providers.yaml"),
        domains=domains,
        sources=sources,
        schedules=_read_yaml(config_dir / "schedules.yaml"),
        env=env,
        ai_reading=ai_reading,
    )
