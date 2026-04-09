from __future__ import annotations

from datetime import datetime, timezone

import feedparser

from auto_report.models.records import CollectedItem
from auto_report.pipeline.source_filters import should_keep_candidate


def parse_rss_content(
    source_id: str,
    content: str,
    category_hint: str,
    max_items: int | None = None,
    source_rules: dict[str, object] | None = None,
) -> list[CollectedItem]:
    parsed = feedparser.parse(content)
    items: list[CollectedItem] = []
    collected_at = datetime.now(timezone.utc).isoformat()
    rules = source_rules or {}

    selected_entries = parsed.entries[:max_items] if max_items else parsed.entries

    for index, entry in enumerate(selected_entries):
        title = entry.get("title", "").strip()
        url = entry.get("link", "").strip()
        if not title or not url:
            continue
        if not should_keep_candidate(title, url, rules):
            continue
        tags = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
        if category_hint and category_hint not in tags:
            tags.append(category_hint)
        summary = (
            entry.get("summary", "").strip()
            or entry.get("description", "").strip()
            or (
                entry.get("content", [{}])[0].get("value", "").strip()
                if entry.get("content")
                else ""
            )
        )
        items.append(
            CollectedItem(
                source_id=source_id,
                item_id=f"{source_id}:{index}",
                title=title,
                url=url,
                summary=summary,
                published_at=entry.get("published", collected_at),
                collected_at=collected_at,
                tags=tags,
                language="unknown",
                metadata={},
            )
        )
    return items
