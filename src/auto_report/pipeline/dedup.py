from __future__ import annotations

from auto_report.models.records import CollectedItem, TopicGroup


def deduplicate_items(items: list[CollectedItem]) -> list[TopicGroup]:
    grouped: dict[str, TopicGroup] = {}
    for item in items:
        key = item.url.strip().lower()
        if key not in grouped:
            grouped[key] = TopicGroup(
                group_id=key,
                canonical_title=item.title,
                canonical_url=item.url,
            )
        grouped[key].evidence_items.append(item)
    return list(grouped.values())
