from __future__ import annotations

from dataclasses import dataclass

from auto_report.models.records import TopicGroup


@dataclass(slots=True)
class DomainMatch:
    primary_domain: str
    matched_domains: list[str]


def classify_topic(topic: TopicGroup) -> DomainMatch:
    haystack = " ".join(
        [topic.canonical_title]
        + [item.summary for item in topic.evidence_items]
        + [" ".join(item.tags) for item in topic.evidence_items]
    ).lower()

    electronics_tokens = ("npu", "accelerator", "embedded", "sensor", "edge ai", "robotics")
    if any(token in haystack for token in electronics_tokens):
        return DomainMatch(
            primary_domain="ai-x-electronics",
            matched_domains=["ai-x-electronics", "ai-llm-agent"],
        )

    return DomainMatch(
        primary_domain="ai-llm-agent",
        matched_domains=["ai-llm-agent"],
    )
