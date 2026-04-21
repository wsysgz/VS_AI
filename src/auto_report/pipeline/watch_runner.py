from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_report.models.records import CollectedItem
from auto_report.settings import load_settings
from auto_report.sources import collector as collector_module
from auto_report.sources.websites import extract_json_items, extract_listing_items, extract_structured_items


WATCH_REGISTRY_PATH = Path("out") / "source-governance" / "changedetection-watch-registry.json"
WATCH_STATE_PATH = Path("out") / "source-governance" / "watch-run-state.json"
WATCH_RESULTS_PATH = Path("out") / "source-governance" / "watch-run-results.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _website_source_lookup(root_dir: Path) -> dict[str, dict[str, Any]]:
    settings = load_settings(root_dir)
    return {
        str(source.get("id", "")).strip(): source
        for source in settings.sources.get("websites", {}).get("sources", [])
        if isinstance(source, dict) and str(source.get("id", "")).strip()
    }


def _collect_watch_items(source: dict[str, Any]) -> list[CollectedItem]:
    mode = str(source.get("mode", "article_listing")).strip() or "article_listing"
    body = collector_module._fetch_source_body(source)
    if mode == "json_api":
        extracted = extract_json_items(source, json.loads(body))
    elif mode == "structured_page":
        extracted = extract_structured_items(source, body)
    else:
        extracted = extract_listing_items(source, body)
    return extracted[: int(source.get("max_items", 12) or 12)]


def _load_state(root_dir: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root_dir / WATCH_STATE_PATH)
    items = payload.get("items", [])
    if not isinstance(items, list):
        return {}
    return {
        str(item.get("source_id", "")).strip(): item
        for item in items
        if isinstance(item, dict) and str(item.get("source_id", "")).strip()
    }


def _item_key(item: CollectedItem) -> str:
    return f"{item.title}|{item.url}"


def run_watch_checks(root_dir: Path) -> Path:
    registry_payload = _load_json(root_dir / WATCH_REGISTRY_PATH)
    registry_items = registry_payload.get("items", [])
    registry_items = registry_items if isinstance(registry_items, list) else []
    registry_by_source = {
        str(item.get("source_id", "")).strip(): item
        for item in registry_items
        if isinstance(item, dict) and str(item.get("source_id", "")).strip()
    }
    website_sources = _website_source_lookup(root_dir)
    existing_state = _load_state(root_dir)
    now = datetime.now(timezone.utc).isoformat()

    results: list[dict[str, Any]] = []
    next_state_items: list[dict[str, Any]] = []
    initialized_count = 0
    changed_count = 0
    unchanged_count = 0
    blocked_count = 0
    active_watch_count = 0

    for raw_item in registry_items:
        if not isinstance(raw_item, dict):
            continue
        status = str(raw_item.get("status", "")).strip() or "planned"
        if status != "active_local":
            continue
        active_watch_count += 1
        source_id = str(raw_item.get("source_id", "")).strip()
        source = website_sources.get(source_id)
        if not isinstance(source, dict):
            registry_entry = registry_by_source.get(source_id, {})
            if isinstance(registry_entry, dict):
                registry_entry["status"] = "blocked"
                registry_entry["note"] = "Missing website source configuration."
                registry_entry["updated_at"] = now
            blocked_count += 1
            results.append(
                {
                    "source_id": source_id,
                    "status": "blocked",
                    "reason": "Missing website source configuration.",
                    "checked_at": now,
                    "new_item_count": 0,
                    "new_items": [],
                }
            )
            continue

        try:
            items = _collect_watch_items(source)
        except Exception as exc:
            registry_entry = registry_by_source.get(source_id, {})
            if isinstance(registry_entry, dict):
                registry_entry["status"] = "blocked"
                registry_entry["note"] = str(exc)
                registry_entry["updated_at"] = now
            blocked_count += 1
            results.append(
                {
                    "source_id": source_id,
                    "status": "blocked",
                    "reason": str(exc),
                    "checked_at": now,
                    "new_item_count": 0,
                    "new_items": [],
                }
            )
            continue

        if not items:
            registry_entry = registry_by_source.get(source_id, {})
            if isinstance(registry_entry, dict):
                registry_entry["status"] = "blocked"
                registry_entry["note"] = "No matching items extracted from the current source configuration."
                registry_entry["updated_at"] = now
            blocked_count += 1
            results.append(
                {
                    "source_id": source_id,
                    "status": "blocked",
                    "reason": "No matching items extracted from the current source configuration.",
                    "checked_at": now,
                    "new_item_count": 0,
                    "new_items": [],
                }
            )
            continue

        current_keys = [_item_key(item) for item in items]
        previous = existing_state.get(source_id, {})
        previous_keys = previous.get("seen_keys", [])
        previous_keys = previous_keys if isinstance(previous_keys, list) else []
        previous_key_set = set(str(value) for value in previous_keys)

        if not previous_key_set:
            initialized_count += 1
            result_status = "initialized"
            new_items: list[dict[str, Any]] = []
            last_change_at = str(previous.get("last_change_at", "")).strip()
        else:
            fresh_items = [item for item in items if _item_key(item) not in previous_key_set]
            if fresh_items:
                changed_count += 1
                result_status = "changed"
                new_items = [
                    {"title": item.title, "url": item.url, "published_at": item.published_at}
                    for item in fresh_items
                ]
                last_change_at = now
                registry_entry = registry_by_source.get(source_id, {})
                if isinstance(registry_entry, dict):
                    registry_entry["status"] = "active_local"
                    registry_entry["note"] = ""
                    registry_entry["updated_at"] = now
            else:
                unchanged_count += 1
                result_status = "unchanged"
                new_items = []
                last_change_at = str(previous.get("last_change_at", "")).strip()
                registry_entry = registry_by_source.get(source_id, {})
                if isinstance(registry_entry, dict):
                    registry_entry["status"] = "active_local"
                    registry_entry["note"] = ""
                    registry_entry["updated_at"] = now

        results.append(
            {
                "source_id": source_id,
                "status": result_status,
                "checked_at": now,
                "new_item_count": len(new_items),
                "new_items": new_items,
            }
        )
        next_state_items.append(
            {
                "source_id": source_id,
                "seen_keys": current_keys,
                "last_checked_at": now,
                "last_change_at": last_change_at,
            }
        )

    state_payload = {
        "generated_at": now,
        "count": len(next_state_items),
        "items": next_state_items,
    }
    results_payload = {
        "generated_at": now,
        "summary": {
            "active_watch_count": active_watch_count,
            "initialized_count": initialized_count,
            "changed_count": changed_count,
            "unchanged_count": unchanged_count,
            "blocked_count": blocked_count,
        },
        "items": results,
    }
    status_counts: dict[str, int] = {}
    for item in registry_items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "planned")).strip() or "planned"
        status_counts[status] = status_counts.get(status, 0) + 1
    registry_payload["generated_at"] = now
    registry_payload["count"] = len(registry_items)
    registry_payload["summary"] = {"status_counts": status_counts}
    registry_payload["items"] = registry_items
    _save_json(root_dir / WATCH_REGISTRY_PATH, registry_payload)
    _save_json(root_dir / WATCH_STATE_PATH, state_payload)
    _save_json(root_dir / WATCH_RESULTS_PATH, results_payload)
    return root_dir / WATCH_RESULTS_PATH
