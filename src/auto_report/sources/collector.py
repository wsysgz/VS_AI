from __future__ import annotations

import json
import re
from typing import Any
import time

import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed

from auto_report.models.records import CollectedItem
from auto_report.settings import Settings
from auto_report.sources.github import normalize_github_repository_detail
from auto_report.sources.hn import fetch_hn_top_stories
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import extract_json_items, extract_listing_items, extract_structured_items

_META_CHARSET_PATTERN = re.compile(br"<meta[^>]+charset=['\"]?([A-Za-z0-9._-]+)", re.IGNORECASE)


def _decode_response_text(response: requests.Response) -> str:
    encoding = str(getattr(response, "encoding", "") or "").strip()
    if encoding and encoding.lower() not in {"iso-8859-1", "latin-1"}:
        return str(getattr(response, "text", ""))

    content = getattr(response, "content", b"")
    if not isinstance(content, bytes):
        content = bytes(content or b"")
    if not content:
        return str(getattr(response, "text", ""))

    meta_match = _META_CHARSET_PATTERN.search(content[:4096])
    if meta_match is not None:
        meta_encoding = meta_match.group(1).decode("ascii", errors="ignore").strip()
        if meta_encoding:
            try:
                return content.decode(meta_encoding, errors="replace")
            except LookupError:
                pass

    apparent_encoding = str(getattr(response, "apparent_encoding", "") or "").strip()
    if apparent_encoding:
        try:
            return content.decode(apparent_encoding, errors="replace")
        except LookupError:
            pass

    if encoding:
        try:
            return content.decode(encoding, errors="replace")
        except LookupError:
            pass

    return str(getattr(response, "text", ""))


def _fetch_text(url: str, timeout: int = 20, retries: int = 1) -> str:
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "auto-report/0.1"},
            )
            response.raise_for_status()
            return _decode_response_text(response)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
            if attempt >= retries:
                raise
            time.sleep(0.3)

    if last_error is not None:
        raise last_error
    raise RuntimeError("unreachable")


def _fetch_source_body(source: dict[str, Any]) -> str:
    fetch_url = str(source.get("api_url") or source["url"])
    timeout = int(source.get("timeout_seconds", 20) or 20)
    method = str(source.get("api_method", "get")).strip().lower() or "get"
    headers = {"User-Agent": "auto-report/0.1"}
    extra_headers = source.get("request_headers", {})
    if isinstance(extra_headers, dict):
        headers.update({str(key): str(value) for key, value in extra_headers.items()})

    if method == "post":
        response = requests.post(
            fetch_url,
            json=source.get("api_request_json", {}),
            timeout=timeout,
            headers=headers,
        )
        response.raise_for_status()
        return _decode_response_text(response)

    return _fetch_text(fetch_url, timeout=timeout)


def _collect_rss(settings: Settings) -> tuple[list[CollectedItem], list[str]]:
    items: list[CollectedItem] = []
    diagnostics: list[str] = []
    for source in settings.sources.get("rss", {}).get("sources", []):
        if not source.get("enabled", False):
            continue
        try:
            timeout = int(source.get("timeout_seconds", 20))
            content = _fetch_text(str(source["url"]), timeout=timeout)
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
    enabled_sources = [
        source
        for source in settings.sources.get("websites", {}).get("sources", [])
        if source.get("enabled", False)
    ]

    def _fetch_one_site(source: dict) -> list[CollectedItem]:
        mode = str(source.get("mode", "article_listing")).strip() or "article_listing"
        body = _fetch_source_body(source)
        if mode == "json_api":
            extracted = extract_json_items(source, json.loads(body))
            return extracted[: int(source.get("max_items", 12))]
        html = body
        if mode == "structured_page":
            extracted = extract_structured_items(source, html)
        else:
            extracted = extract_listing_items(source, html)
        return extracted[: int(source.get("max_items", 12))]

    if not enabled_sources:
        return items, diagnostics

    results_by_index: dict[int, list[CollectedItem]] = {}
    max_workers = min(6, len(enabled_sources))

    completed_futures: set[Any] = set()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_meta = {
            executor.submit(_fetch_one_site, source): (index, source)
            for index, source in enumerate(enabled_sources)
        }
        try:
            for future in as_completed(future_to_meta, timeout=60):
                completed_futures.add(future)
                index, source = future_to_meta[future]
                try:
                    results_by_index[index] = future.result(timeout=25)
                except Exception as exc:
                    diagnostics.append(f"Website source failed: {source.get('id')} -> {exc}")
        except FuturesTimeoutError:
            pending_sources = [
                str(source.get("id"))
                for future, (_, source) in future_to_meta.items()
                if future not in completed_futures and not future.done()
            ]
            if pending_sources:
                diagnostics.append(f"Website collectors timed out: {', '.join(pending_sources)}")
            for future in future_to_meta:
                if not future.done():
                    future.cancel()

    for index in range(len(enabled_sources)):
        items.extend(results_by_index.get(index, []))

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

    executor = ThreadPoolExecutor(max_workers=4)
    completed_futures: set[Any] = set()
    try:
        future_to_name = {
            executor.submit(collector, settings): collector.__name__
            for collector in collectors
        }
        try:
            for future in as_completed(future_to_name, timeout=120):
                completed_futures.add(future)
                name = future_to_name[future]
                try:
                    items, messages = future.result()
                    all_items.extend(items)
                    diagnostics.extend(messages)
                except Exception as exc:
                    diagnostics.append(f"{name} collection timeout or error: {exc}")
        except FuturesTimeoutError:
            pending_names = [
                future_to_name[future]
                for future in future_to_name
                if future not in completed_futures
            ]
            if pending_names:
                diagnostics.append(f"Collectors timed out: {', '.join(pending_names)}")
            for future in future_to_name:
                if future not in completed_futures and not future.done():
                    future.cancel()
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return all_items, diagnostics
