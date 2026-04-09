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

    env = {
        "DEEPSEEK_API_KEY": os.environ.get("DEEPSEEK_API_KEY", ""),
        "AI_PROVIDER": os.environ.get("AI_PROVIDER", "deepseek"),
        "AI_BASE_URL": os.environ.get("AI_BASE_URL", "https://api.deepseek.com"),
        "AI_MODEL": os.environ.get("AI_MODEL", "deepseek-chat"),
        "PUSHPLUS_TOKEN": os.environ.get("PUSHPLUS_TOKEN", ""),
        "PUSHPLUS_CHANNEL": os.environ.get("PUSHPLUS_CHANNEL", "clawbot"),
        "PUSHPLUS_FALLBACK_CHANNEL": os.environ.get("PUSHPLUS_FALLBACK_CHANNEL", ""),
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_CHAT_ID": os.environ.get("TELEGRAM_CHAT_ID", ""),
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
        "REPORT_REPO_URL": os.environ.get("REPORT_REPO_URL", "https://github.com/wsysgz/VS_AI"),
        "AUTO_TIMEZONE": os.environ.get("AUTO_TIMEZONE", "Asia/Shanghai"),
        "AUTO_PUSH_ENABLED": os.environ.get("AUTO_PUSH_ENABLED", "true"),
        "AUTO_ARCHIVE_TO_GITHUB": os.environ.get("AUTO_ARCHIVE_TO_GITHUB", "true"),
    }

    return Settings(
        root_dir=resolved_root,
        providers=_read_yaml(config_dir / "providers.yaml"),
        domains=domains,
        sources=sources,
        schedules=_read_yaml(config_dir / "schedules.yaml"),
        env=env,
    )
