from __future__ import annotations

import json
from pathlib import Path


def _normalize_label(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("/", "-")


def build_review_issue_candidates(payload: dict[str, object], limit: int = 3) -> list[dict[str, object]]:
    signal_lookup: dict[tuple[str, str], dict[str, object]] = {}
    for raw_signal in payload.get("signals", []):
        if not isinstance(raw_signal, dict):
            continue
        key = (
            str(raw_signal.get("title", "")).strip(),
            str(raw_signal.get("url", "")).strip(),
        )
        signal_lookup[key] = raw_signal

    candidates: list[tuple[int, float, dict[str, object]]] = []
    for raw_analysis in payload.get("analyses", []):
        if not isinstance(raw_analysis, dict):
            continue
        title = str(raw_analysis.get("title", "")).strip()
        url = str(raw_analysis.get("url", "")).strip()
        if not title or not url:
            continue

        signal = signal_lookup.get((title, url), {})
        score = float(signal.get("score", 0.0))
        risk_level = str(raw_analysis.get("risk_level", signal.get("risk_level", "low"))).strip() or "low"
        lifecycle_state = str(
            raw_analysis.get("lifecycle_state", signal.get("lifecycle_state", "new"))
        ).strip() or "new"
        support_evidence = raw_analysis.get("support_evidence", [])
        has_external_support = any(
            isinstance(item, dict) and str(item.get("evidence_scope", "")).strip() == "external"
            for item in support_evidence
        )

        priority = 0
        if score >= 3.0:
            priority += 2
        if risk_level == "high":
            priority += 3
        elif risk_level == "medium":
            priority += 2
        if lifecycle_state in {"new", "rising"}:
            priority += 1
        if not has_external_support:
            priority += 1

        if priority < 4:
            continue

        evidence_lines = [
            f"- {item.get('source_type', 'unknown')} | {item.get('title', '')} | {item.get('url', '')}"
            for item in support_evidence[:5]
            if isinstance(item, dict)
        ] or ["- None"]

        body = "\n".join(
            [
                f"Title: {title}",
                f"URL: {url}",
                f"Domain: {raw_analysis.get('primary_domain', signal.get('primary_domain', 'unknown'))}",
                f"Score: {score:.1f}",
                f"Risk level: {risk_level}",
                f"Lifecycle: {lifecycle_state}",
                f"Confidence: {raw_analysis.get('confidence', 'low')}",
                "",
                "Core insight:",
                str(raw_analysis.get("core_insight", "")).strip() or "-",
                "",
                "Primary contradiction:",
                str(raw_analysis.get("primary_contradiction", "")).strip() or "-",
                "",
                "Enrichment summary:",
                str(raw_analysis.get("enrichment", {}).get("summary", "")).strip() or "-",
                "",
                "Support evidence:",
                *evidence_lines,
            ]
        )

        domain = str(raw_analysis.get("primary_domain", signal.get("primary_domain", "unknown"))).strip() or "unknown"
        issue = {
            "title": f"[V7 review] {title}",
            "body": body,
            "labels": [
                "review",
                "high-value",
                f"risk-{_normalize_label(risk_level)}",
                f"domain-{_normalize_label(domain)}",
            ],
            "meta": {
                "title": title,
                "url": url,
                "score": round(score, 1),
                "risk_level": risk_level,
                "lifecycle_state": lifecycle_state,
                "has_external_support": has_external_support,
            },
        }
        candidates.append((priority, score, issue))

    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]["title"]))
    return [item[2] for item in candidates[:limit]]


def _lead_bucket_rows(payload: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    rows: list[tuple[str, dict[str, object]]] = []
    for bucket in ("official_feed_leads", "rsshub_leads", "changedetection_leads"):
        for item in payload.get(bucket, []):
            if isinstance(item, dict):
                rows.append((bucket, item))
    return rows


def _lead_confidence_score(value: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(value.strip().lower(), 0)


def _lead_bucket_score(bucket: str) -> int:
    return {
        "official_feed_leads": 30,
        "rsshub_leads": 20,
        "changedetection_leads": 10,
    }.get(bucket, 0)


def _source_registry_url_map(payload: dict[str, object]) -> dict[str, str]:
    source_registry = payload.get("source_registry", {})
    if not isinstance(source_registry, dict):
        return {}
    mapping: dict[str, str] = {}
    for source_id, item in source_registry.items():
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if url:
            mapping[url.rstrip("/").lower()] = str(source_id).strip()
    return mapping


def _priority_source_ids(payload: dict[str, object]) -> set[str]:
    source_governance = payload.get("source_governance", {})
    if not isinstance(source_governance, dict):
        return set()
    queue = source_governance.get("priority_queue", [])
    if not isinstance(queue, list):
        return set()
    ids = set()
    for item in queue:
        if isinstance(item, dict):
            source_id = str(item.get("source_id", "")).strip()
            if source_id:
                ids.add(source_id)
    return ids


def _match_source_id(payload: dict[str, object], item: dict[str, object]) -> str:
    url_map = _source_registry_url_map(payload)
    url = str(item.get("url", "")).strip().rstrip("/").lower()
    if url and url in url_map:
        return url_map[url]
    return ""


def _lead_priority_score(bucket: str, item: dict[str, object]) -> int:
    score = _lead_bucket_score(bucket)
    confidence = str(item.get("confidence", "")).strip()
    classification = str(item.get("classification", "")).strip()
    score += _lead_confidence_score(confidence) * 10
    if classification == "official-feed":
        score += 12
    elif classification == "official-site":
        score += 8
    elif classification == "rsshub-candidate":
        score += 6
    elif classification == "changedetection-candidate":
        score += 4

    if str(item.get("feed_candidate", "")).strip():
        score += 4
    if str(item.get("rsshub_candidate", "")).strip():
        score += 3
    if str(item.get("changedetection_candidate", "")).strip():
        score += 2
    return score


def _lead_priority_label(score: int) -> str:
    if score >= 60:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _lead_key(bucket: str, item: dict[str, object]) -> str:
    keyword = str(item.get("keyword", "")).strip()
    title = str(item.get("title", "")).strip()
    url = str(item.get("url", "")).strip() or str(item.get("classification", "")).strip()
    return f"{bucket}|{keyword}|{title}|{url}"


def build_source_lead_review_candidates(
    payload: dict[str, object],
    limit_per_kind: int = 2,
) -> list[dict[str, object]]:
    seen: set[tuple[str, str, str]] = set()
    bucket_counts: dict[str, int] = {}
    issues: list[dict[str, object]] = []
    priority_source_ids = _priority_source_ids(payload)

    ordered_rows = sorted(
        _lead_bucket_rows(payload),
        key=lambda row: (
            -(
                _lead_priority_score(row[0], row[1])
                + (
                    40 if _match_source_id(payload, row[1]) else 0
                )
                + (
                    20 if _match_source_id(payload, row[1]) in priority_source_ids else 0
                )
            ),
            str(row[1].get("keyword", "")),
            str(row[1].get("title", "")),
        ),
    )

    for bucket, item in ordered_rows:
        bucket_count = bucket_counts.get(bucket, 0)
        if bucket_count >= limit_per_kind:
            continue

        keyword = str(item.get("keyword", "")).strip()
        title = str(item.get("title", "")).strip()
        classification = str(item.get("classification", "")).strip() or "unknown"
        url = str(item.get("url", "")).strip()
        confidence = str(item.get("confidence", "")).strip() or "unknown"
        source_id = _match_source_id(payload, item)
        priority_score = _lead_priority_score(bucket, item)
        if source_id:
            priority_score += 40
        if source_id in priority_source_ids:
            priority_score += 20
        priority_label = _lead_priority_label(priority_score)
        dedupe_key = (keyword, title, url or classification)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        body_lines = [
            f"Keyword: {keyword or '-'}",
            f"Lead type: {bucket}",
            f"Title: {title or '-'}",
            f"Classification: {classification}",
            f"Confidence: {confidence}",
            f"URL: {url or '-'}",
            f"Feed candidate: {str(item.get('feed_candidate', '')).strip() or '-'}",
            f"RSSHub candidate: {str(item.get('rsshub_candidate', '')).strip() or '-'}",
            f"changedetection candidate: {str(item.get('changedetection_candidate', '')).strip() or '-'}",
            f"Next action: {str(item.get('next_action', '')).strip() or '-'}",
        ]
        issues.append(
            {
                "title": f"[Lead review] {keyword or title or classification}",
                "body": "\n".join(body_lines),
                "labels": [
                    "review",
                    "source-governance",
                    f"lead-{_normalize_label(bucket.replace('_leads', ''))}",
                    f"priority-{priority_label}",
                    f"confidence-{_normalize_label(confidence)}",
                ],
                "meta": {
                    "lead_key": _lead_key(bucket, item),
                    "keyword": keyword,
                    "title": title,
                    "classification": classification,
                    "confidence": confidence,
                    "bucket": bucket,
                    "url": url,
                    "source_id": source_id,
                    "priority_score": priority_score,
                    "priority_label": priority_label,
                },
            }
        )
        bucket_counts[bucket] = bucket_count + 1

    return issues


def build_source_lead_review_payload(
    payload: dict[str, object],
    limit_per_kind: int = 2,
) -> dict[str, object]:
    issues = build_source_lead_review_candidates(payload, limit_per_kind=limit_per_kind)
    clusters_map: dict[str, dict[str, object]] = {}
    bucket_counts: dict[str, int] = {}
    priority_counts = {"high": 0, "medium": 0, "low": 0}

    for issue in issues:
        meta = issue.get("meta", {}) if isinstance(issue.get("meta"), dict) else {}
        keyword = str(meta.get("keyword", "")).strip() or "(unknown)"
        bucket = str(meta.get("bucket", "")).strip() or "unknown"
        priority_score = int(meta.get("priority_score", 0) or 0)
        priority_label = str(meta.get("priority_label", "low")).strip() or "low"
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if priority_label in priority_counts:
            priority_counts[priority_label] += 1

        cluster = clusters_map.setdefault(
            keyword,
            {
                "keyword": keyword,
                "priority_score": priority_score,
                "priority_label": priority_label,
                "issue_count": 0,
                "buckets": [],
                "lead_keys": [],
                "titles": [],
                "source_ids": [],
            },
        )
        cluster["priority_score"] = max(int(cluster["priority_score"]), priority_score)
        cluster["priority_label"] = _lead_priority_label(int(cluster["priority_score"]))
        cluster["issue_count"] = int(cluster["issue_count"]) + 1
        if bucket not in cluster["buckets"]:
            cluster["buckets"].append(bucket)
        lead_key = str(meta.get("lead_key", "")).strip()
        if lead_key and lead_key not in cluster["lead_keys"]:
            cluster["lead_keys"].append(lead_key)
        title = str(meta.get("title", "")).strip()
        if title and title not in cluster["titles"]:
            cluster["titles"].append(title)
        source_id = str(meta.get("source_id", "")).strip()
        if source_id and source_id not in cluster["source_ids"]:
            cluster["source_ids"].append(source_id)

    clusters = sorted(
        clusters_map.values(),
        key=lambda item: (
            -int(item["priority_score"]),
            -int(item["issue_count"]),
            str(item["keyword"]),
        ),
    )
    issues.sort(
        key=lambda issue: (
            -int(issue.get("meta", {}).get("priority_score", 0)),
            str(issue.get("meta", {}).get("keyword", "")),
            str(issue.get("meta", {}).get("title", "")),
        )
    )
    return {
        "count": len(issues),
        "summary": {
            "bucket_counts": bucket_counts,
            "priority_counts": priority_counts,
            "cluster_count": len(clusters),
        },
        "clusters": clusters,
        "issues": issues,
    }


def _load_existing_source_lead_review_status(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get("items", [])
    if not isinstance(items, list):
        return {}
    existing: dict[str, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        lead_key = str(item.get("lead_key", "")).strip()
        if lead_key:
            existing[lead_key] = item
    return existing


def build_source_lead_review_status_payload(
    issues_payload: dict[str, object],
    existing_status_path: Path,
) -> dict[str, object]:
    existing = _load_existing_source_lead_review_status(existing_status_path)
    items: list[dict[str, object]] = []
    for issue in issues_payload.get("issues", []):
        if not isinstance(issue, dict):
            continue
        meta = issue.get("meta", {})
        if not isinstance(meta, dict):
            continue
        lead_key = str(meta.get("lead_key", "")).strip()
        if not lead_key:
            continue
        previous = existing.get(lead_key, {})
        items.append(
            {
                "lead_key": lead_key,
                "keyword": str(meta.get("keyword", "")).strip(),
                "title": str(meta.get("title", "")).strip(),
                "bucket": str(meta.get("bucket", "")).strip(),
                "priority_score": int(meta.get("priority_score", 0) or 0),
                "priority_label": str(meta.get("priority_label", "low")).strip() or "low",
                "status": str(previous.get("status", "pending")).strip() or "pending",
                "note": str(previous.get("note", "")).strip(),
                "updated_at": str(previous.get("updated_at", "")).strip(),
            }
        )
    return {
        "count": len(items),
        "items": items,
    }


def _status_lookup(status_payload: dict[str, object]) -> dict[str, dict[str, object]]:
    lookup: dict[str, dict[str, object]] = {}
    for item in status_payload.get("items", []):
        if not isinstance(item, dict):
            continue
        lead_key = str(item.get("lead_key", "")).strip()
        if lead_key:
            lookup[lead_key] = item
    return lookup


def _source_registry_lookup(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    source_registry = payload.get("source_registry", {})
    if not isinstance(source_registry, dict):
        return {}
    return {
        str(source_id).strip(): item
        for source_id, item in source_registry.items()
        if isinstance(item, dict)
    }


def _target_kind_for_issue(issue: dict[str, object]) -> str:
    meta = issue.get("meta", {})
    if not isinstance(meta, dict):
        return "unknown"
    bucket = str(meta.get("bucket", "")).strip()
    if bucket == "official_feed_leads":
        return "official_feed"
    if bucket == "rsshub_leads":
        return "rsshub"
    if bucket == "changedetection_leads":
        return "changedetection"
    return "unknown"


def _candidate_value_for_issue(issue: dict[str, object], target_kind: str) -> str:
    body = str(issue.get("body", ""))
    for line in body.splitlines():
        if target_kind == "official_feed" and line.startswith("Feed candidate: "):
            return line.removeprefix("Feed candidate: ").strip()
        if target_kind == "rsshub" and line.startswith("RSSHub candidate: "):
            return line.removeprefix("RSSHub candidate: ").strip()
        if target_kind == "changedetection" and line.startswith("changedetection candidate: "):
            return line.removeprefix("changedetection candidate: ").strip()
    return ""


def _infer_source_id(issue: dict[str, object]) -> str:
    meta = issue.get("meta", {})
    if not isinstance(meta, dict):
        return ""
    keyword = str(meta.get("keyword", "")).strip().lower()
    url = str(meta.get("url", "")).strip().lower()
    title = str(meta.get("title", "")).strip().lower()

    if "anthropic" in keyword or "anthropic.com/news" in url or "anthropic" in title:
        return "anthropic-news"
    if "qualcomm" in keyword or "qualcomm.com/news/onq" in url or "qualcomm" in title:
        return "qualcomm-onq"
    if "jetson" in keyword or "developer.nvidia.com" in url or "jetson" in title:
        return "nvidia-embedded"
    return ""


def _remote_validation_required(source_id: str, target_kind: str) -> bool:
    if source_id == "anthropic-news":
        return True
    return False


def _target_file_for_update(source_id: str, target_kind: str, source_info: dict[str, object]) -> str:
    if target_kind in {"official_feed", "rsshub"}:
        return "config/sources/rss.yaml"
    collector = str(source_info.get("collector", "")).strip()
    if collector == "github":
        return "config/sources/github.yaml"
    if collector == "rss":
        return "config/sources/rss.yaml"
    return "config/sources/websites.yaml"


def _validation_mode_for_update(source_id: str, target_kind: str) -> str:
    if source_id == "anthropic-news":
        return "remote_feed_validation"
    if target_kind in {"official_feed", "rsshub"}:
        return "local_feed_validation"
    if target_kind == "changedetection":
        return "remote_watch_validation"
    return "manual_review"


def _suggested_fields_for_update(
    issue: dict[str, object],
    target_kind: str,
    source_info: dict[str, object],
) -> dict[str, object]:
    meta = issue.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    fields: dict[str, object] = {
        "id": str(meta.get("source_id", "")).strip(),
        "category_hint": str(source_info.get("category_hint", "")).strip(),
    }
    candidate_value = _candidate_value_for_issue(issue, target_kind)
    if target_kind in {"official_feed", "rsshub"}:
        fields.update(
            {
                "collector": "rss",
                "enabled": True,
                "mode": "rss_feed",
                "url": candidate_value,
            }
        )
    elif target_kind == "changedetection":
        fields.update(
            {
                "collector": str(source_info.get("collector", "")).strip() or "websites",
                "enabled": bool(source_info.get("enabled", True)),
                "mode": str(source_info.get("mode", "")).strip() or "article_listing",
                "url": candidate_value,
                "watch_strategy": "changedetection-watch",
            }
        )
    return {key: value for key, value in fields.items() if value not in {"", None}}


def build_approved_source_lead_updates(
    issues: list[dict[str, object]],
    status_payload: dict[str, object],
    governance_payload: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    status_lookup = _status_lookup(status_payload)
    source_registry = _source_registry_lookup(governance_payload or {})
    emitted_source_ids: set[str] = set()
    updates: list[dict[str, object]] = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        meta = issue.get("meta", {})
        if not isinstance(meta, dict):
            continue
        lead_key = str(meta.get("lead_key", "")).strip()
        if not lead_key:
            continue
        status = status_lookup.get(lead_key, {})
        if str(status.get("status", "")).strip() != "approved":
            continue
        target_kind = _target_kind_for_issue(issue)
        source_id = _infer_source_id(issue)
        source_info = source_registry.get(source_id, {}) if source_id else {}
        note = str(status.get("note", "")).strip()
        if source_id and source_id in emitted_source_ids:
            continue
        emitted_source_ids.add(source_id)

        # anthropic-news is already validated as a working website listing in this repo.
        # The "approved" action should therefore capture the current source as the
        # executable target rather than forcing a broken RSS migration.
        if source_id == "anthropic-news":
            target_kind = "validated_listing"
            remote_validation_required = False
            validation_mode = "remote_listing_validation"
            apply_ready = True
            blocking_reason = ""
            current_url = str(source_info.get("url", "")).strip() or str(meta.get("url", "")).strip()
            candidate_value = current_url
            target_file = "config/sources/websites.yaml"
            suggested_fields = {
                "id": "anthropic-news",
                "collector": str(source_info.get("collector", "")).strip() or "websites",
                "enabled": bool(source_info.get("enabled", True)),
                "mode": str(source_info.get("mode", "")).strip() or "article_listing",
                "url": current_url,
                "category_hint": str(source_info.get("category_hint", "")).strip(),
                "stability_tier": "verified-listing",
                "watch_strategy": "listing-poll",
                "replacement_target": str(source_info.get("replacement_target", "")).strip() or "none",
                "candidate_kind": "validated_listing",
                "candidate_value": current_url,
            }
            current_source = {
                "collector": str(source_info.get("collector", "")).strip(),
                "enabled": bool(source_info.get("enabled", False)),
                "mode": str(source_info.get("mode", "")).strip(),
                "url": current_url,
            }
            remote_validation_required = False
        else:
            remote_validation_required = _remote_validation_required(source_id, target_kind)
            validation_mode = _validation_mode_for_update(source_id, target_kind)
            apply_ready = not remote_validation_required
            blocking_reason = ""
            if remote_validation_required:
                blocking_reason = "Requires remote validation before applying this source update."
            candidate_value = _candidate_value_for_issue(issue, target_kind)
            target_file = _target_file_for_update(source_id, target_kind, source_info)
            suggested_fields = _suggested_fields_for_update(issue, target_kind, source_info)
            current_source = {
                "collector": str(source_info.get("collector", "")).strip(),
                "enabled": bool(source_info.get("enabled", False)),
                "mode": str(source_info.get("mode", "")).strip(),
                "url": str(source_info.get("url", "")).strip(),
            }
        updates.append(
            {
                "lead_key": lead_key,
                "keyword": str(meta.get("keyword", "")).strip(),
                "title": str(meta.get("title", "")).strip(),
                "bucket": str(meta.get("bucket", "")).strip(),
                "source_id": source_id,
                "status": "approved",
                "note": note,
                "target_kind": target_kind,
                "candidate_value": candidate_value,
                "target_file": target_file,
                "suggested_fields": suggested_fields,
                "current_source": current_source,
                "validation_mode": validation_mode,
                "remote_validation_required": remote_validation_required,
                "apply_ready": apply_ready,
                "blocking_reason": blocking_reason,
                "recommended_next_step": (
                    "Run a remote validation after updating this source."
                    if remote_validation_required
                    else "Update the source candidate locally and verify the next run."
                ),
                "priority_score": int(meta.get("priority_score", 0) or 0),
                "priority_label": str(meta.get("priority_label", "low")).strip() or "low",
            }
        )

    updates.sort(
        key=lambda item: (
            -int(item.get("priority_score", 0)),
            str(item.get("keyword", "")),
            str(item.get("title", "")),
        )
    )
    return updates


def load_source_governance_payload(root_dir: Path) -> dict[str, object]:
    path = root_dir / "out" / "source-governance" / "source-governance.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
