from __future__ import annotations

import json
from pathlib import Path


STAGE_FILE_NAMES = {
    "analysis": "analysis-before.md",
    "summary": "summary-before.md",
    "forecast": "forecast-before.md",
}
REGISTRY_FILE_NAME = "registry.json"


def _load_legacy_registry(base_dir: Path) -> dict[str, list[dict[str, object]]]:
    registry: dict[str, list[dict[str, object]]] = {}
    for stage, file_name in STAGE_FILE_NAMES.items():
        path = base_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing AI reading asset for {stage}: {path}")
        registry[stage] = [
            {
                "id": f"{stage}-legacy",
                "stage": stage,
                "version": "legacy",
                "path": str(path),
                "tags": ["compat"],
                "meta": {},
                "active": True,
                "content": path.read_text(encoding="utf-8").strip(),
            }
        ]
    return registry


def _load_single_legacy_entry(base_dir: Path, stage: str) -> list[dict[str, object]]:
    file_name = STAGE_FILE_NAMES[stage]
    path = base_dir / file_name
    if not path.exists():
        raise FileNotFoundError(f"Missing AI reading asset for {stage}: {path}")
    return [
        {
            "id": f"{stage}-legacy",
            "stage": stage,
            "version": "legacy",
            "path": str(path),
            "tags": ["compat"],
            "meta": {},
            "active": True,
            "content": path.read_text(encoding="utf-8").strip(),
        }
    ]


def _normalize_manifest_entry(base_dir: Path, stage: str, raw_entry: dict[str, object]) -> dict[str, object]:
    relative_path = str(raw_entry.get("path", "")).strip()
    path = base_dir / relative_path
    if not relative_path or not path.exists():
        raise FileNotFoundError(f"Missing prompt asset for {stage}: {path}")

    tags = [str(tag).strip() for tag in raw_entry.get("tags", []) if str(tag).strip()]
    return {
        "id": str(raw_entry.get("id") or f"{stage}-{raw_entry.get('version', 'unknown')}").strip(),
        "stage": stage,
        "version": str(raw_entry.get("version", "unknown")).strip() or "unknown",
        "path": str(path),
        "tags": tags,
        "meta": raw_entry.get("meta") or raw_entry.get("metadata") or {},
        "active": bool(raw_entry.get("active", False)),
        "content": path.read_text(encoding="utf-8").strip(),
    }


def load_prompt_registry(root_dir: Path) -> dict[str, list[dict[str, object]]]:
    base_dir = root_dir / "config" / "ai_reading"
    manifest_path = base_dir / REGISTRY_FILE_NAME
    if not manifest_path.exists():
        return _load_legacy_registry(base_dir)

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Prompt registry manifest must be a JSON object: {manifest_path}")

    registry: dict[str, list[dict[str, object]]] = {}
    for stage, raw_entries in payload.items():
        if not isinstance(raw_entries, list):
            raise ValueError(f"Prompt registry stage '{stage}' must be a list")
        registry[stage] = [_normalize_manifest_entry(base_dir, stage, entry) for entry in raw_entries]

    for stage in STAGE_FILE_NAMES:
        if stage not in registry:
            registry[stage] = _load_single_legacy_entry(base_dir, stage)

    return registry


def _pick_active_entry(entries: list[dict[str, object]]) -> dict[str, object]:
    for entry in entries:
        if entry.get("active"):
            return entry
    return entries[0]


def load_ai_readings(root_dir: Path) -> dict[str, str]:
    registry = load_prompt_registry(root_dir)
    readings: dict[str, str] = {}
    for stage in STAGE_FILE_NAMES:
        entries = registry.get(stage, [])
        if not entries:
            raise FileNotFoundError(f"Missing AI reading asset for {stage}: {root_dir / 'config' / 'ai_reading'}")
        readings[stage] = str(_pick_active_entry(entries)["content"]).strip()
    return readings
