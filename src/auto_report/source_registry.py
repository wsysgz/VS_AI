from __future__ import annotations


def _default_stability_tier(collector: str, enabled: bool, mode: str) -> str:
    if not enabled:
        return "manual-watch"
    if collector == "websites":
        return "dynamic-site" if mode == "browser_flow" else "fragile-listing"
    if collector == "hacker_news":
        return "dynamic-site"
    return "stable-feed"


def _default_replacement_hint(collector: str, enabled: bool) -> str:
    if not enabled:
        return "Keep disabled until a stable source entry point is confirmed"
    if collector == "websites":
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
        return "Create a changedetection watch for this URL and store the watch reference."
    if candidate_kind == "rsshub_route":
        return "Validate an RSSHub route and replace this source with the feed."
    if candidate_kind == "manual_replace":
        return "Review this source and replace it with the preferred target."
    return "Keep the current source under routine observation."


def _source_metadata(source: dict[str, object], *, collector: str, mode: str) -> dict[str, object]:
    enabled = bool(source.get("enabled", False))
    stability_tier = str(source.get("stability_tier", "")).strip()
    replacement_hint = str(source.get("replacement_hint", "")).strip()
    watch_strategy = str(source.get("watch_strategy", "")).strip()
    replacement_target = str(source.get("replacement_target", "")).strip()
    url = str(source.get("url", "")).strip()
    resolved_watch_strategy = watch_strategy or _default_watch_strategy(collector, enabled, mode)
    resolved_replacement_target = replacement_target or _default_replacement_target(collector, enabled)
    candidate_kind = _default_candidate_kind(collector, resolved_watch_strategy, resolved_replacement_target)
    candidate_value = _default_candidate_value(url, candidate_kind, resolved_replacement_target)
    return {
        "stability_tier": stability_tier or _default_stability_tier(collector, enabled, mode),
        "replacement_hint": replacement_hint or _default_replacement_hint(collector, enabled),
        "watch_strategy": resolved_watch_strategy,
        "replacement_target": resolved_replacement_target,
        "candidate_kind": candidate_kind,
        "candidate_value": candidate_value,
        "automation_ready": candidate_kind in {"rsshub_route", "changedetection_watch"},
        "next_action": _default_next_action(candidate_kind),
    }


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
        for repository in repositories:
            registry[repository] = {
                "collector": "github",
                "enabled": bool(source.get("enabled", False)),
                "mode": mode,
                "category_hint": str(source.get("category_hint", "")).strip(),
                "source_group": source_id,
                "url": f"https://github.com/{repository}",
                **_source_metadata(source, collector="github", mode=mode),
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
            }
        )

    manual_review = [row for row in rows if row["watch_strategy"] == "manual-review"]
    rsshub_candidates = [row for row in rows if "rsshub" in row["replacement_target"]]
    changedetection_candidates = [row for row in rows if row["candidate_kind"] == "changedetection_watch"]
    replacement_candidates = [row for row in rows if row["replacement_target"] not in ("", "none")]

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
        "replacement_candidates": replacement_candidates,
    }
