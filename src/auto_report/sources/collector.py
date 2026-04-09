from __future__ import annotations

from typing import Any

import requests

from auto_report.models.records import CollectedItem
from auto_report.settings import Settings
from auto_report.sources.github import normalize_github_repository_detail
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import extract_listing_items


def _fetch_text(url: str, timeout: int = 20) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "auto-report/0.1"},
    )
    response.raise_for_status()
    return response.text


def _collect_rss(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    items: list[CollectedItem] = []
    diagnostics: list[str] = []
    for source in settings.sources.get("rss", {}).get("sources", []):
        if not source.get("enabled", False):
            continue
        try:
            content = _fetch_text(str(source["url"]))
            items.extend(
                parse_rss_content(
                    source_id=str(source["id"]),
                    content=content,
                    category_hint=str(source.get("category_hint", "")),
                    max_items=int(source.get("max_items", 20)),
                    source_rules=source,
                )
            )
        except Exception as exc:
            diagnostics.append(f"RSS source failed: {source.get('id')} -> {exc}")
    return items, diagnostics


def _collect_github(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    items: list[CollectedItem] = []
    diagnostics: list[str] = []
    token = settings.env.get("GITHUB_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for source in settings.sources.get("github", {}).get("sources", []):
        if not source.get("enabled", False):
            continue
        if source.get("mode") != "curated_repositories":
            continue
        try:
            repositories = [
                str(repository).strip()
                for repository in source.get("repositories", [])
                if str(repository).strip()
            ]
            for full_name in repositories[: int(source.get("max_items", len(repositories) or 0))]:
                response = requests.get(
                    f"https://api.github.com/repos/{full_name}",
                    timeout=20,
                    headers=headers,
                )
                response.raise_for_status()
                item = normalize_github_repository_detail(
                    source_id=str(source["id"]),
                    payload=response.json(),
                    category_hint=str(source.get("category_hint", "")),
                )
                if item is not None:
                    items.append(item)
        except Exception as exc:
            diagnostics.append(f"GitHub source failed: {source.get('id')} -> {exc}")
    return items, diagnostics


def _collect_websites(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    items: list[CollectedItem] = []
    diagnostics: list[str] = []
    for source in settings.sources.get("websites", {}).get("sources", []):
        if not source.get("enabled", False):
            continue
        try:
            html = _fetch_text(str(source["url"]))
            extracted = extract_listing_items(source, html)
            items.extend(extracted[: int(source.get("max_items", 12))])
        except Exception as exc:
            diagnostics.append(f"Website source failed: {source.get('id')} -> {exc}")
    return items, diagnostics


def collect_all_items(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    all_items: list[CollectedItem] = []
    diagnostics: list[str] = []
    for collector in (_collect_rss, _collect_github, _collect_websites):
        items, messages = collector(settings)
        all_items.extend(items)
        diagnostics.extend(messages)
    return all_items, diagnostics
