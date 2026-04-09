from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CollectedItem:
    source_id: str
    item_id: str
    title: str
    url: str
    summary: str
    published_at: str
    collected_at: str
    tags: list[str]
    language: str
    metadata: dict[str, object]


@dataclass(slots=True)
class TopicGroup:
    group_id: str
    canonical_title: str
    canonical_url: str
    evidence_items: list[CollectedItem] = field(default_factory=list)
