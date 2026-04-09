from __future__ import annotations

from auto_report.models.records import TopicGroup


def score_topic(topic: TopicGroup) -> float:
    evidence_count = len(topic.evidence_items)
    title = topic.canonical_title.lower()
    keyword_bonus = 1.0 if any(token in title for token in ("agent", "llm", "npu", "accelerator")) else 0.0
    return evidence_count + keyword_bonus
