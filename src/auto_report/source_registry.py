from __future__ import annotations


COMPARISON_METADATA_FIELDS = (
    "region_scope",
    "org_origin",
    "tech_track",
    "comparison_priority",
)


def _default_stability_tier(collector: str, enabled: bool, mode: str) -> str:
    if not enabled:
        return "manual-watch"
    if collector == "websites":
        if mode == "json_api":
            return "stable-api"
        if mode == "structured_page":
            return "stable-page"
        return "dynamic-site" if mode == "browser_flow" else "fragile-listing"
    if collector == "hacker_news":
        return "dynamic-site"
    return "stable-feed"


def _default_replacement_hint(collector: str, enabled: bool, mode: str = "") -> str:
    if not enabled:
        return "Keep disabled until a stable source entry point is confirmed"
    if collector == "websites":
        if mode == "json_api":
            return "Poll the official JSON endpoint directly and keep field mappings aligned with the API payload"
        if mode == "structured_page":
            return "Poll the official update page directly and keep selectors aligned with its entry structure"
        return "Prefer a stable RSS/RSSHub feed or monitored fallback if this listing becomes noisy"
    if collector == "hacker_news":
        return "Treat as opportunistic discovery rather than a guaranteed source"
    return ""


def _default_watch_strategy(collector: str, enabled: bool, mode: str) -> str:
    if not enabled:
        return "manual-review"
    if collector == "rss":
        return "feed-poll"
    if collector == "github":
        return "repo-poll"
    if collector == "websites":
        if mode == "json_api":
            return "api-poll"
        if mode == "structured_page":
            return "page-poll"
        return "browser-watch" if mode == "browser_flow" else "listing-poll"
    if collector == "hacker_news":
        return "opportunistic-poll"
    return "manual-review"


def _default_replacement_target(collector: str, enabled: bool) -> str:
    if not enabled:
        return "stable-listing"
    if collector == "websites":
        return "rsshub-or-feed"
    if collector == "hacker_news":
        return "none"
    return "none"


def _default_candidate_kind(collector: str, watch_strategy: str, replacement_target: str) -> str:
    if collector == "websites" and watch_strategy in {"listing-poll", "browser-watch"}:
        return "changedetection_watch"
    if "rsshub" in replacement_target:
        return "rsshub_route"
    if replacement_target not in ("", "none"):
        return "manual_replace"
    return "none"


def _default_candidate_value(url: str, candidate_kind: str, replacement_target: str) -> str:
    if candidate_kind == "changedetection_watch":
        return url
    if candidate_kind in {"rsshub_route", "manual_replace"}:
        return replacement_target
    return ""


def _default_next_action(candidate_kind: str) -> str:
    if candidate_kind == "changedetection_watch":
        return "Activate the repo-local watch runner for this URL and keep its baseline/results up to date."
    if candidate_kind == "rsshub_route":
        return "Validate an RSSHub route and replace this source with the feed."
    if candidate_kind == "manual_replace":
        return "Review this source and replace it with the preferred target."
    return "Keep the current source under routine observation."


def _priority_score(row: dict[str, object]) -> int:
    candidate_kind = str(row.get("candidate_kind") or "")
    category_hint = str(row.get("category_hint") or "")
    stability_tier = str(row.get("stability_tier") or "")
    enabled = bool(row.get("enabled", False))

    score = {
        "manual_replace": 90,
        "changedetection_watch": 70,
        "rsshub_route": 60,
    }.get(candidate_kind, 0)

    if category_hint in {"ai-llm-agent", "ai-x-electronics"}:
        score += 10

    if enabled and stability_tier in {"fragile-listing", "manual-watch"}:
        score += 10

    return score


def _priority_label(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 65:
        return "medium"
    return "low"


def _priority_reason(row: dict[str, object], score: int) -> str:
    candidate_kind = str(row.get("candidate_kind") or "none")
    category_hint = str(row.get("category_hint") or "")
    stability_tier = str(row.get("stability_tier") or "")
    enabled = bool(row.get("enabled", False))
    parts = [candidate_kind]
    if category_hint:
        parts.append(category_hint)
    if stability_tier:
        parts.append(stability_tier)
    parts.append("enabled" if enabled else "disabled")
    parts.append(f"score={score}")
    return ", ".join(parts)


def _source_metadata(source: dict[str, object], *, collector: str, mode: str) -> dict[str, object]:
    enabled = bool(source.get("enabled", False))
    stability_tier = str(source.get("stability_tier", "")).strip()
    replacement_hint = str(source.get("replacement_hint", "")).strip()
    watch_strategy = str(source.get("watch_strategy", "")).strip()
    replacement_target = str(source.get("replacement_target", "")).strip()
    explicit_candidate_kind = str(source.get("candidate_kind", "")).strip()
    explicit_candidate_value = str(source.get("candidate_value", "")).strip()
    explicit_next_action = str(source.get("next_action", "")).strip()
    url = str(source.get("url", "")).strip()
    resolved_watch_strategy = watch_strategy or _default_watch_strategy(collector, enabled, mode)
    if collector == "websites" and mode in {"structured_page", "json_api"}:
        resolved_replacement_target = replacement_target or "none"
    else:
        resolved_replacement_target = replacement_target or _default_replacement_target(collector, enabled)
    candidate_kind = explicit_candidate_kind or _default_candidate_kind(collector, resolved_watch_strategy, resolved_replacement_target)
    candidate_value = explicit_candidate_value or _default_candidate_value(url, candidate_kind, resolved_replacement_target)
    metadata = {
        "stability_tier": stability_tier or _default_stability_tier(collector, enabled, mode),
        "replacement_hint": replacement_hint or _default_replacement_hint(collector, enabled, mode),
        "watch_strategy": resolved_watch_strategy,
        "replacement_target": resolved_replacement_target,
        "candidate_kind": candidate_kind,
        "candidate_value": candidate_value,
        "automation_ready": bool(source.get("automation_ready", candidate_kind in {"rsshub_route", "changedetection_watch"})),
        "next_action": explicit_next_action or _default_next_action(candidate_kind),
    }
    for field in COMPARISON_METADATA_FIELDS:
        metadata[field] = str(source.get(field, "")).strip()
    return metadata


def build_source_registry(settings) -> dict[str, dict[str, object]]:
    registry: dict[str, dict[str, object]] = {}

    for source in settings.sources.get("rss", {}).get("sources", []):
        source_id = str(source.get("id", "")).strip()
        if source_id:
            mode = "rss_feed"
            registry[source_id] = {
                "collector": "rss",
                "enabled": bool(source.get("enabled", False)),
                "mode": mode,
                "category_hint": str(source.get("category_hint", "")).strip(),
                "source_group": source_id,
                "url": str(source.get("url", "")).strip(),
                **_source_metadata(source, collector="rss", mode=mode),
            }

    for source in settings.sources.get("websites", {}).get("sources", []):
        source_id = str(source.get("id", "")).strip()
        if source_id:
            mode = str(source.get("mode", "article_listing")).strip() or "article_listing"
            registry[source_id] = {
                "collector": "websites",
                "enabled": bool(source.get("enabled", False)),
                "mode": mode,
                "category_hint": str(source.get("category_hint", "")).strip(),
                "source_group": source_id,
                "url": str(source.get("url", "")).strip(),
                **_source_metadata(source, collector="websites", mode=mode),
            }

    for source in settings.sources.get("github", {}).get("sources", []):
        source_id = str(source.get("id", "")).strip()
        repositories = [
            str(repository).strip()
            for repository in source.get("repositories", [])
            if str(repository).strip()
        ]
        mode = str(source.get("mode", "curated_repositories")).strip() or "curated_repositories"
        repository_metadata = source.get("repository_metadata", {})
        repository_metadata = repository_metadata if isinstance(repository_metadata, dict) else {}
        for repository in repositories:
            metadata = _source_metadata(source, collector="github", mode=mode)
            raw_repo_metadata = repository_metadata.get(repository, {})
            repo_metadata = raw_repo_metadata if isinstance(raw_repo_metadata, dict) else {}
            for field in COMPARISON_METADATA_FIELDS:
                value = str(repo_metadata.get(field, metadata.get(field, ""))).strip()
                metadata[field] = value
            registry[repository] = {
                "collector": "github",
                "enabled": bool(source.get("enabled", False)),
                "mode": mode,
                "category_hint": str(source.get("category_hint", "")).strip(),
                "source_group": source_id,
                "url": f"https://github.com/{repository}",
                **metadata,
            }

    registry["hacker_news"] = {
        "collector": "hacker_news",
        "enabled": bool(settings.sources.get("hacker_news", {}).get("enabled", False)),
        "mode": "top_stories",
        "category_hint": "",
        "source_group": "hacker_news",
        "url": "https://news.ycombinator.com/",
        "stability_tier": _default_stability_tier("hacker_news", bool(settings.sources.get("hacker_news", {}).get("enabled", False)), "top_stories"),
        "replacement_hint": _default_replacement_hint("hacker_news", bool(settings.sources.get("hacker_news", {}).get("enabled", False))),
        "watch_strategy": _default_watch_strategy("hacker_news", bool(settings.sources.get("hacker_news", {}).get("enabled", False)), "top_stories"),
        "replacement_target": _default_replacement_target("hacker_news", bool(settings.sources.get("hacker_news", {}).get("enabled", False))),
        "region_scope": "",
        "org_origin": "",
        "tech_track": "",
        "comparison_priority": "",
    }

    return registry


def build_source_governance_queue(source_registry: dict[str, dict[str, object]]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for source_id, raw_item in sorted(source_registry.items()):
        item = raw_item if isinstance(raw_item, dict) else {}
        rows.append(
            {
                "source_id": source_id,
                "collector": str(item.get("collector") or ""),
                "enabled": bool(item.get("enabled", False)),
                "mode": str(item.get("mode") or ""),
                "category_hint": str(item.get("category_hint") or ""),
                "stability_tier": str(item.get("stability_tier") or ""),
                "watch_strategy": str(item.get("watch_strategy") or ""),
                "replacement_target": str(item.get("replacement_target") or ""),
                "candidate_kind": str(item.get("candidate_kind") or ""),
                "candidate_value": str(item.get("candidate_value") or ""),
                "automation_ready": bool(item.get("automation_ready", False)),
                "next_action": str(item.get("next_action") or ""),
                "replacement_hint": str(item.get("replacement_hint") or ""),
                "source_group": str(item.get("source_group") or ""),
                "url": str(item.get("url") or ""),
                "region_scope": str(item.get("region_scope") or ""),
                "org_origin": str(item.get("org_origin") or ""),
                "tech_track": str(item.get("tech_track") or ""),
                "comparison_priority": str(item.get("comparison_priority") or ""),
            }
        )

    manual_review = [row for row in rows if row["watch_strategy"] == "manual-review"]
    rsshub_candidates = [row for row in rows if "rsshub" in row["replacement_target"]]
    changedetection_candidates = [row for row in rows if row["candidate_kind"] == "changedetection_watch"]
    replacement_candidates = [row for row in rows if row["replacement_target"] not in ("", "none")]
    changedetection_watch_list = [
        {
            **row,
            "watch_target": row["url"],
            "priority_score": _priority_score(row),
            "priority_label": _priority_label(_priority_score(row)),
            "reason": _priority_reason(row, _priority_score(row)),
        }
        for row in changedetection_candidates
    ]
    changedetection_watch_list.sort(key=lambda row: (-int(row["priority_score"]), str(row["source_id"])))

    priority_queue = [
        {
            **row,
            "watch_target": row["url"] if row["candidate_kind"] == "changedetection_watch" else "",
            "priority_score": _priority_score(row),
            "priority_label": _priority_label(_priority_score(row)),
            "reason": _priority_reason(row, _priority_score(row)),
        }
        for row in rows
        if row["candidate_kind"] in {"manual_replace", "changedetection_watch", "rsshub_route"}
    ]
    priority_queue.sort(key=lambda row: (-int(row["priority_score"]), str(row["source_id"])))

    return {
        "summary": {
            "manual_review_count": len(manual_review),
            "rsshub_candidate_count": len(rsshub_candidates),
            "changedetection_candidate_count": len(changedetection_candidates),
            "replacement_candidate_count": len(replacement_candidates),
        },
        "manual_review": manual_review,
        "rsshub_candidates": rsshub_candidates,
        "changedetection_candidates": changedetection_candidates,
        "changedetection_watch_list": changedetection_watch_list,
        "replacement_candidates": replacement_candidates,
        "priority_queue": priority_queue,
    }
