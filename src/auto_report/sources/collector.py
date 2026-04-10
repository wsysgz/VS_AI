from __future__ import annotations

from typing import Any

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from auto_report.models.records import CollectedItem
from auto_report.settings import Settings
from auto_report.sources.github import normalize_github_repository_detail
from auto_report.sources.hn import fetch_hn_top_stories
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

    def _fetch_one_repo(full_name: str) -> CollectedItem | None:
        response = requests.get(
            f"https://api.github.com/repos/{full_name}",
            timeout=20,
            headers=headers,
        )
        response.raise_for_status()
        item = normalize_github_repository_detail(
            source_id="curated-repos",
            payload=response.json(),
            category_hint="ai-llm-agent",
        )
        return item

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

            # 并发抓取所有仓库 (最多5路)
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(_fetch_one_repo, repo): repo
                    for repo in repositories[: int(source.get("max_items", len(repositories) or 0))]
                }
                for future in as_completed(futures, timeout=60):
                    try:
                        item = future.result(timeout=30)
                        if item is not None:
                            items.append(item)
                    except Exception as exc:
                        diagnostics.append(f"GitHub repo failed: {futures[future]} -> {exc}")
        except Exception as exc:
            diagnostics.append(f"GitHub source failed: {source.get('id')} -> {exc}")
    return items, diagnostics


def _collect_websites(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    items: list[CollectedItem] = []
    diagnostics: list[str] = []

    def _fetch_one_site(source: dict) -> list[CollectedItem]:
        url = str(source["url"])
        html = _fetch_text(url)
        extracted = extract_listing_items(source, html)
        return extracted[: int(source.get("max_items", 12))]

    for source in settings.sources.get("websites", {}).get("sources", []):
        if not source.get("enabled", False):
            continue
        # 单个网站抓取保持同步（每个网站内部可能有复杂解析逻辑）
        # 但如果源很多，可以用线程池
        try:
            html = _fetch_text(str(source["url"]))
            extracted = extract_listing_items(source, html)
            items.extend(extracted[: int(source.get("max_items", 12))])
        except Exception as exc:
            diagnostics.append(f"Website source failed: {source.get('id')} -> {exc}")
    return items, diagnostics


def _collect_hn(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    """采集 Hacker News 热门故事（仅 AI/芯片/开源相关）"""
    diagnostics: list[str] = []
    hn_config = settings.sources.get("hacker_news", {})

    if not hn_config.get("enabled", False):
        return [], diagnostics

    try:
        items, msgs = fetch_hn_top_stories(
            max_items=int(hn_config.get("max_items", 20)),
            min_score=int(hn_config.get("min_score", 10)),
        )
        diagnostics.extend(msgs)
        return items, diagnostics
    except Exception as exc:
        diagnostics.append(f"HN source failed: {exc}")
        return [], diagnostics


def collect_all_items(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    """并发采集所有数据源：RSS / GitHub / Website / HN 四大类并行启动"""
    all_items: list[CollectedItem] = []
    diagnostics: list[str] = []

    collectors = [_collect_rss, _collect_github, _collect_websites, _collect_hn]

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_name = {
            executor.submit(collector, settings): collector.__name__
            for collector in collectors
        }
        for future in as_completed(future_to_name, timeout=120):
            name = future_to_name[future]
            try:
                items, messages = future.result(timeout=90)
                all_items.extend(items)
                diagnostics.extend(messages)
            except Exception as exc:
                diagnostics.append(f"{name} collection timeout or error: {exc}")

    return all_items, diagnostics
