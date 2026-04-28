from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml

from auto_report.sources import collector as collector_module
from auto_report.sources.rss import parse_rss_content
from auto_report.sources.websites import extract_json_items, extract_listing_items, extract_sitemap_items, extract_structured_items


OUTPUT_PATH = Path("out") / "source-governance" / "source-candidate-validation.json"
MARKDOWN_PATH = Path("out") / "source-governance" / "source-candidate-validation.md"
DISCOVERY_SEARCH_PATH = Path("out") / "discovery-search" / "discovery-search.json"
_CURL_META_MARKER = "\n__AUTO_REPORT_CURL_META__"


def _is_http_url(value: object) -> bool:
    text = str(value or "").strip()
    return text.startswith(("http://", "https://"))


def _looks_like_feed(text: str) -> bool:
    lowered = text[:500].lower()
    return "<rss" in lowered or "<feed" in lowered


def _probe_requests(url: str, timeout_seconds: int) -> dict[str, object]:
    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": "auto-report/0.1"},
        )
        text = response.text or ""
        return {
            "status": "ok",
            "http_status": response.status_code,
            "final_url": response.url,
            "content_type": response.headers.get("content-type", ""),
            "byte_count": len(response.content),
            "looks_like_feed": _looks_like_feed(text),
        }
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}


def _probe_curl(url: str, timeout_seconds: int) -> dict[str, object]:
    curl_path = shutil.which("curl")
    if not curl_path:
        return {"status": "failed", "error": "curl executable not found"}
    try:
        completed = subprocess.run(
            [
                curl_path,
                "-L",
                "-A",
                "Mozilla/5.0 auto-report/0.1",
                "--max-time",
                str(timeout_seconds),
                "--silent",
                "--show-error",
                "--write-out",
                f"{_CURL_META_MARKER}%{{http_code}}|%{{url_effective}}|%{{content_type}}",
                url,
            ],
            capture_output=True,
            check=True,
            timeout=timeout_seconds + 5,
        )
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}

    output = completed.stdout.decode("utf-8", errors="replace")
    body, marker, meta = output.rpartition(_CURL_META_MARKER)
    if not marker:
        body = output
        meta = ""
    http_status, final_url, content_type = (meta.split("|", 2) + ["", "", ""])[:3]
    try:
        parsed_status: int | str = int(http_status)
    except ValueError:
        parsed_status = http_status
    return {
        "status": "ok",
        "http_status": parsed_status,
        "final_url": final_url,
        "content_type": content_type,
        "byte_count": len(body.encode("utf-8")),
        "looks_like_feed": _looks_like_feed(body),
    }


def _probe_url(url: str, timeout_seconds: int = 20) -> dict[str, object]:
    return {
        "url": url,
        "requests": _probe_requests(url, timeout_seconds),
        "curl": _probe_curl(url, timeout_seconds),
    }


def _load_discovery_urls(path: Path) -> list[str]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []

    urls: list[str] = []
    seen: set[str] = set()
    for item in items:
        candidates = item.get("candidates", []) if isinstance(item, dict) else []
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            for field in ("feed_candidate", "url", "changedetection_candidate"):
                url = str(candidate.get(field, "")).strip()
                if _is_http_url(url) and url not in seen:
                    urls.append(url)
                    seen.add(url)
                    break
    return urls


def _configured_source_lookup(root_dir: Path) -> dict[str, tuple[str, dict[str, Any]]]:
    lookup: dict[str, tuple[str, dict[str, Any]]] = {}
    for collector_name, relative_path in (
        ("rss", Path("config") / "sources" / "rss.yaml"),
        ("websites", Path("config") / "sources" / "websites.yaml"),
    ):
        path = root_dir / relative_path
        if not path.exists():
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        sources = payload.get("sources", []) if isinstance(payload, dict) else []
        if not isinstance(sources, list):
            continue
        for source in sources:
            if isinstance(source, dict) and str(source.get("id", "")).strip():
                lookup[str(source.get("id", "")).strip()] = (collector_name, source)
    return lookup


def _extract_configured_source(collector_name: str, source: dict[str, Any]) -> dict[str, object]:
    try:
        if collector_name == "rss":
            body = collector_module._fetch_text(str(source.get("url", "")), timeout=int(source.get("timeout_seconds", 20) or 20))
            items = parse_rss_content(
                source_id=str(source.get("id", "")),
                content=body,
                category_hint=str(source.get("category_hint", "")),
                max_items=int(source.get("max_items", 20) or 20),
                source_rules=source,
            )
        else:
            body = collector_module._fetch_source_body(source)
            mode = str(source.get("mode", "article_listing")).strip() or "article_listing"
            if mode == "json_api":
                items = extract_json_items(source, json.loads(body))
            elif mode == "sitemap":
                items = extract_sitemap_items(source, body)
            elif mode == "structured_page":
                items = extract_structured_items(source, body)
            else:
                items = extract_listing_items(source, body)
            items = items[: int(source.get("max_items", 12) or 12)]
    except Exception as exc:
        return {"status": "failed", "error": str(exc), "item_count": 0, "sample_items": []}

    return {
        "status": "ok",
        "item_count": len(items),
        "sample_items": [
            {
                "title": item.title,
                "url": item.url,
                "published_at": item.published_at,
            }
            for item in items[:5]
        ],
    }


def _render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Source Candidate Validation",
        "",
        f"- Generated at: {payload.get('generated_at', '-')}",
        f"- Count: {payload.get('count', 0)}",
        "",
        "| source_id | url | requests | curl | collector_items |",
        "|---|---|---|---|---|",
    ]
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        probe = item.get("probe", {}) if isinstance(item.get("probe", {}), dict) else {}
        requests_probe = probe.get("requests", {}) if isinstance(probe.get("requests", {}), dict) else {}
        curl_probe = probe.get("curl", {}) if isinstance(probe.get("curl", {}), dict) else {}
        collector = item.get("collector", {}) if isinstance(item.get("collector", {}), dict) else {}
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("source_id", "")),
                    str(item.get("url", "")),
                    str(requests_probe.get("http_status", requests_probe.get("status", ""))),
                    str(curl_probe.get("http_status", curl_probe.get("status", ""))),
                    str(collector.get("item_count", "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines).strip() + "\n"


def validate_source_candidates(
    root_dir: Path,
    *,
    urls: list[str] | None = None,
    source_ids: list[str] | None = None,
    input_path: Path | None = None,
    timeout_seconds: int = 20,
) -> Path:
    configured_sources = _configured_source_lookup(root_dir)
    items: list[dict[str, object]] = []

    for source_id in source_ids or []:
        source_key = str(source_id or "").strip()
        if not source_key:
            continue
        collector_name, source = configured_sources.get(source_key, ("", {}))
        if not source:
            items.append(
                {
                    "source_id": source_key,
                    "url": "",
                    "kind": "configured-source",
                    "collector": {"status": "failed", "error": "source id not found", "item_count": 0},
                }
            )
            continue
        items.append(
            {
                "source_id": source_key,
                "url": str(source.get("url", "")),
                "kind": "configured-source",
                "collector": _extract_configured_source(collector_name, source),
            }
        )

    candidate_urls = [url for url in urls or [] if _is_http_url(url)]
    if not candidate_urls and not source_ids:
        candidate_urls = _load_discovery_urls(input_path or root_dir / DISCOVERY_SEARCH_PATH)

    seen_urls: set[str] = set()
    for url in candidate_urls:
        if url in seen_urls:
            continue
        seen_urls.add(url)
        items.append(
            {
                "source_id": "",
                "url": url,
                "kind": "url",
                "probe": _probe_url(url, timeout_seconds=timeout_seconds),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
    }

    output_path = root_dir / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (root_dir / MARKDOWN_PATH).write_text(_render_markdown(payload), encoding="utf-8")
    return output_path
