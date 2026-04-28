from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


SOURCE_FILE_MAP = {
    "rss": Path("config") / "sources" / "rss.yaml",
    "websites": Path("config") / "sources" / "websites.yaml",
    "github": Path("config") / "sources" / "github.yaml",
}

OUTPUT_PATH = Path("out") / "review-queue" / "applied-source-updates.json"
CANDIDATE_UPDATES_PATH = Path("out") / "review-queue" / "candidate-updates.json"
WATCH_REGISTRY_PATH = Path("out") / "source-governance" / "changedetection-watch-registry.json"

SOURCE_FIELD_ORDER = [
    "id",
    "enabled",
    "mode",
    "url",
    "fetch_backend",
    "api_url",
    "category_hint",
    "max_items",
    "stability_tier",
    "replacement_hint",
    "watch_strategy",
    "replacement_target",
    "candidate_kind",
    "candidate_value",
    "next_action",
    "automation_ready",
    "entry_selector",
    "title_selector",
    "link_selector",
    "date_selector",
    "entry_link_is_self",
    "sitemap_reverse_order",
    "json_items_path",
    "json_items_slice_start",
    "item_title_field",
    "item_link_field",
    "item_link_template",
    "item_date_field",
    "include_url_patterns",
    "include_title_patterns",
    "exclude_url_patterns",
    "exclude_title_patterns",
    "timeout_seconds",
    "repositories",
]


def _read_yaml_payload(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {"sources": []}
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        payload["sources"] = []
    return payload


def _write_yaml_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_json_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _ordered_source(source: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in SOURCE_FIELD_ORDER:
        if key in source:
            ordered[key] = source[key]
    for key, value in source.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _find_source_index(sources: list[dict[str, Any]], source_id: str) -> int:
    for index, source in enumerate(sources):
        if str(source.get("id", "")).strip() == source_id:
            return index
    return -1


def _remove_source(sources: list[dict[str, Any]], source_id: str) -> dict[str, Any]:
    index = _find_source_index(sources, source_id)
    if index < 0:
        return {}
    removed = sources.pop(index)
    return removed if isinstance(removed, dict) else {}


def _upsert_source(sources: list[dict[str, Any]], source: dict[str, Any]) -> None:
    source_id = str(source.get("id", "")).strip()
    index = _find_source_index(sources, source_id)
    ordered = _ordered_source(source)
    if index < 0:
        sources.append(ordered)
        return
    sources[index] = ordered


def _load_source_sets(root_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        name: _read_yaml_payload(root_dir / relative_path)
        for name, relative_path in SOURCE_FILE_MAP.items()
    }


def _load_watch_registry(root_dir: Path) -> dict[str, Any]:
    payload = _read_json_payload(root_dir / WATCH_REGISTRY_PATH)
    items = payload.get("items", [])
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def _existing_source(source_sets: dict[str, dict[str, Any]], source_id: str) -> tuple[str, dict[str, Any]]:
    for name, payload in source_sets.items():
        sources = payload.get("sources", [])
        if not isinstance(sources, list):
            continue
        index = _find_source_index(sources, source_id)
        if index >= 0:
            entry = sources[index]
            return name, entry if isinstance(entry, dict) else {}
    return "", {}


def _base_source_entry(
    source_id: str,
    source_sets: dict[str, dict[str, Any]],
    suggested_fields: dict[str, Any],
) -> dict[str, Any]:
    _, existing = _existing_source(source_sets, source_id)
    entry = dict(existing)
    entry.update(
        {
            "id": source_id,
            "enabled": bool(suggested_fields.get("enabled", entry.get("enabled", True))),
            "category_hint": suggested_fields.get("category_hint", entry.get("category_hint", "")),
            "max_items": int(entry.get("max_items", 6) or 6),
        }
    )
    return entry


def _build_feed_entry(
    update: dict[str, Any],
    source_sets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_id = str(update.get("source_id", "")).strip()
    suggested_fields = update.get("suggested_fields", {})
    if not isinstance(suggested_fields, dict):
        suggested_fields = {}
    entry = _base_source_entry(source_id, source_sets, suggested_fields)
    entry.update(
        {
            "id": source_id,
            "enabled": True,
            "url": str(update.get("candidate_value", "")).strip(),
            "stability_tier": "stable-feed",
            "replacement_hint": "",
            "watch_strategy": "feed-poll",
            "replacement_target": "none",
        }
    )
    entry.pop("mode", None)
    entry.pop("candidate_kind", None)
    entry.pop("candidate_value", None)
    entry.pop("next_action", None)
    entry.pop("link_selector", None)
    entry.pop("entry_selector", None)
    entry.pop("title_selector", None)
    entry.pop("date_selector", None)
    entry.pop("entry_link_is_self", None)
    entry.pop("api_url", None)
    entry.pop("json_items_path", None)
    entry.pop("json_items_slice_start", None)
    entry.pop("item_title_field", None)
    entry.pop("item_link_field", None)
    entry.pop("item_link_template", None)
    entry.pop("item_date_field", None)
    return entry


def _build_website_entry(
    update: dict[str, Any],
    source_sets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_id = str(update.get("source_id", "")).strip()
    suggested_fields = update.get("suggested_fields", {})
    if not isinstance(suggested_fields, dict):
        suggested_fields = {}
    entry = _base_source_entry(source_id, source_sets, suggested_fields)
    entry.update(suggested_fields)
    entry["id"] = source_id
    entry["enabled"] = bool(suggested_fields.get("enabled", entry.get("enabled", True)))
    entry["mode"] = str(suggested_fields.get("mode", entry.get("mode", "article_listing"))).strip() or "article_listing"
    entry["url"] = str(suggested_fields.get("url", update.get("candidate_value", entry.get("url", "")))).strip()
    if not entry.get("max_items"):
        entry["max_items"] = 6
    entry.pop("collector", None)
    return entry


def _apply_single_update(
    update: dict[str, Any],
    source_sets: dict[str, dict[str, Any]],
    watch_registry: dict[str, Any],
) -> dict[str, Any]:
    source_id = str(update.get("source_id", "")).strip()
    target_kind = str(update.get("target_kind", "")).strip()
    apply_ready = bool(update.get("apply_ready", False))
    blocking_reason = str(update.get("blocking_reason", "")).strip()

    if not apply_ready:
        return {
            "source_id": source_id,
            "target_kind": target_kind,
            "status": "skipped",
            "reason": blocking_reason or "Update is not apply-ready.",
        }
    if not source_id:
        return {
            "source_id": source_id,
            "target_kind": target_kind,
            "status": "skipped",
            "reason": "Missing source id.",
        }

    if target_kind == "official_feed":
        entry = _build_feed_entry(update, source_sets)
        for name in ("websites", "github", "rss"):
            sources = source_sets[name].get("sources", [])
            if isinstance(sources, list):
                _remove_source(sources, source_id)
        rss_sources = source_sets["rss"].get("sources", [])
        if isinstance(rss_sources, list):
            _upsert_source(rss_sources, entry)
        return {
            "source_id": source_id,
            "target_kind": target_kind,
            "status": "applied",
            "target_file": str(SOURCE_FILE_MAP["rss"]),
            "modified_sets": ["rss", "websites", "github"],
        }

    if target_kind in {"validated_listing", "changedetection"}:
        entry = _build_website_entry(update, source_sets)
        website_sources = source_sets["websites"].get("sources", [])
        if isinstance(website_sources, list):
            _upsert_source(website_sources, entry)
        return {
            "source_id": source_id,
            "target_kind": target_kind,
            "status": "applied",
            "target_file": str(SOURCE_FILE_MAP["websites"]),
            "modified_sets": ["websites"],
        }

    if target_kind == "changedetection_watch":
        items = watch_registry.get("items", [])
        if not isinstance(items, list):
            items = []
            watch_registry["items"] = items
        index = next(
            (
                idx
                for idx, item in enumerate(items)
                if isinstance(item, dict) and str(item.get("source_id", "")).strip() == source_id
            ),
            -1,
        )
        existing = items[index] if index >= 0 and isinstance(items[index], dict) else {}
        updated = {
            **existing,
            "source_id": source_id,
            "watch_target": str(update.get("candidate_value", "")).strip(),
            "status": str(update.get("suggested_fields", {}).get("status", "active_local")).strip() or "active_local",
            "note": str(update.get("suggested_fields", {}).get("note", existing.get("note", ""))).strip(),
            "next_action": str(update.get("suggested_fields", {}).get("next_action", "Run local watch checks.")).strip(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if index >= 0:
            items[index] = updated
        else:
            items.append(updated)
        return {
            "source_id": source_id,
            "target_kind": target_kind,
            "status": "applied",
            "target_file": str(WATCH_REGISTRY_PATH),
            "modified_sets": ["watch_registry"],
        }

    return {
        "source_id": source_id,
        "target_kind": target_kind,
        "status": "skipped",
        "reason": f"Unsupported target kind: {target_kind}",
    }


def _load_candidate_updates(root_dir: Path) -> list[dict[str, Any]]:
    path = root_dir / CANDIDATE_UPDATES_PATH
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    updates = payload.get("updates", [])
    if not isinstance(updates, list):
        return []
    return [item for item in updates if isinstance(item, dict)]


def apply_source_updates(root_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    source_sets = _load_source_sets(root_dir)
    watch_registry = _load_watch_registry(root_dir)
    updates = _load_candidate_updates(root_dir)
    results = [_apply_single_update(update, source_sets, watch_registry) for update in updates]
    modified_sets = sorted(
        {
            modified_name
            for item in results
            if item.get("status") == "applied"
            for modified_name in item.get("modified_sets", [])
            if isinstance(modified_name, str)
        }
    )

    if not dry_run:
        for name in modified_sets:
            if name == "watch_registry":
                items = watch_registry.get("items", [])
                items = items if isinstance(items, list) else []
                items.sort(key=lambda item: (-int(item.get("priority_score", 0) or 0), str(item.get("source_id", ""))))
                status_counts: dict[str, int] = {}
                for item in items:
                    status = str(item.get("status", "planned")).strip() or "planned"
                    status_counts[status] = status_counts.get(status, 0) + 1
                watch_registry["generated_at"] = datetime.now(timezone.utc).isoformat()
                watch_registry["count"] = len(items)
                watch_registry["summary"] = {"status_counts": status_counts}
                output_path = root_dir / WATCH_REGISTRY_PATH
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(watch_registry, ensure_ascii=False, indent=2), encoding="utf-8")
                continue
            payload = source_sets.get(name)
            if not isinstance(payload, dict):
                continue
            _write_yaml_payload(root_dir / SOURCE_FILE_MAP[name], payload)

    applied = [item for item in results if item.get("status") == "applied"]
    skipped = [item for item in results if item.get("status") != "applied"]
    summary = {
        "dry_run": dry_run,
        "count": len(results),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied_source_count": len([item for item in applied if item.get("target_kind") != "changedetection_watch"]),
        "applied_watch_count": len([item for item in applied if item.get("target_kind") == "changedetection_watch"]),
        "skipped_blocked_count": len([item for item in skipped if item.get("reason")]),
        "modified_files": [
            str(WATCH_REGISTRY_PATH) if name == "watch_registry" else str(SOURCE_FILE_MAP[name])
            for name in modified_sets
        ],
        "results": results,
    }

    output_path = root_dir / OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
