from __future__ import annotations

from auto_report.domains.classifier import classify_topic
from auto_report.models.records import CollectedItem, TopicCandidate
from auto_report.pipeline.dedup import deduplicate_items


def build_topic_candidates(items: list[CollectedItem]) -> list[TopicCandidate]:
    topics = deduplicate_items(items)
    candidates: list[TopicCandidate] = []

    for topic in topics:
        domain_match = classify_topic(topic)

        # Build enriched evidence snippets with source attribution and more context
        snippets: list[str] = []
        for item in topic.evidence_items:
            text = item.summary.strip()
            if text:
                # Prepend source ID so AI can assess cross-source corroboration
                src_label = f"[{item.source_id}]"
                snippets.append(f"{src_label} {text}")

        candidates.append(
            TopicCandidate(
                topic_id=topic.group_id,
                title=topic.canonical_title,
                url=topic.canonical_url,
                primary_domain=domain_match.primary_domain,
                matched_domains=domain_match.matched_domains,
                evidence_count=len(topic.evidence_items),
                source_ids=sorted({item.source_id for item in topic.evidence_items}),
                tags=sorted({tag for item in topic.evidence_items for tag in item.tags if tag}),
                evidence_snippets=snippets[:8],
            )
        )

    return candidates
