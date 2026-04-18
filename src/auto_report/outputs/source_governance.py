from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from auto_report.settings import load_settings
from auto_report.source_registry import build_source_governance_queue, build_source_registry


def _load_discovery_search_payload(root_dir: Path) -> dict[str, object]:
    path = root_dir / "out" / "discovery-search" / "discovery-search.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _lead_priority(candidate: dict[str, object]) -> tuple[int, int, str]:
    confidence = str(candidate.get("confidence", "")).strip().lower()
    classification = str(candidate.get("classification", "")).strip()
    confidence_score = {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)
    classification_score = {
        "official-feed": 3,
        "official-site": 2,
        "rsshub-candidate": 2,
        "changedetection-candidate": 2,
    }.get(classification, 0)
    url = str(candidate.get("url", "")).strip()
    return (-confidence_score, -classification_score, url)


def _build_lead_views(discovery_search: dict[str, object]) -> dict[str, list[dict[str, object]]]:
    items = discovery_search.get("items", [])
    if not isinstance(items, list):
        return {
            "official_feed_leads": [],
            "rsshub_leads": [],
            "changedetection_leads": [],
        }

    official_feed_leads: list[dict[str, object]] = []
    rsshub_leads: list[dict[str, object]] = []
    changedetection_leads: list[dict[str, object]] = []
    seen_official: set[str] = set()
    seen_rsshub: set[str] = set()
    seen_changedetection: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword", "")).strip()
        candidates = item.get("candidates", [])
        if not isinstance(candidates, list):
            continue

        sorted_candidates = sorted(
            [candidate for candidate in candidates if isinstance(candidate, dict)],
            key=_lead_priority,
        )

        for candidate in sorted_candidates:
            base = {
                "keyword": keyword,
                "title": str(candidate.get("title", "")).strip(),
                "url": str(candidate.get("url", "")).strip(),
                "classification": str(candidate.get("classification", "")).strip(),
                "confidence": str(candidate.get("confidence", "")).strip(),
                "feed_candidate": str(candidate.get("feed_candidate", "")).strip(),
                "rsshub_candidate": str(candidate.get("rsshub_candidate", "")).strip(),
                "changedetection_candidate": str(candidate.get("changedetection_candidate", "")).strip(),
                "next_action": str(candidate.get("next_action", "")).strip(),
            }

            feed_candidate = base["feed_candidate"]
            rsshub_candidate = base["rsshub_candidate"]
            changedetection_candidate = base["changedetection_candidate"]

            if (
                base["classification"] in {"official-feed", "official-site"}
                and feed_candidate
                and feed_candidate not in seen_official
            ):
                official_feed_leads.append(base)
                seen_official.add(feed_candidate)

            if rsshub_candidate and rsshub_candidate not in seen_rsshub:
                rsshub_leads.append(base)
                seen_rsshub.add(rsshub_candidate)

            if changedetection_candidate and changedetection_candidate not in seen_changedetection:
                changedetection_leads.append(base)
                seen_changedetection.add(changedetection_candidate)

    return {
        "official_feed_leads": official_feed_leads,
        "rsshub_leads": rsshub_leads,
        "changedetection_leads": changedetection_leads,
    }


def build_source_governance_artifact(root_dir: Path) -> Path:
    settings = load_settings(root_dir)
    source_registry = build_source_registry(settings)
    source_governance = build_source_governance_queue(source_registry)
    discovery_search = _load_discovery_search_payload(root_dir)
    discovery_leads = _build_lead_views(discovery_search)

    output_dir = root_dir / "out" / "source-governance"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "source-governance.json"
    output_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_registry": source_registry,
                "source_governance": source_governance,
                "discovery_search": discovery_search,
                **discovery_leads,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path
