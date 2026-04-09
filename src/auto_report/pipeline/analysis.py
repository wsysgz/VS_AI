from __future__ import annotations

from dataclasses import asdict, dataclass

from auto_report.domains.classifier import classify_topic
from auto_report.models.records import CollectedItem, TopicGroup
from auto_report.pipeline.dedup import deduplicate_items
from auto_report.pipeline.scoring import score_topic
from auto_report.pipeline.topic_builder import build_topic_candidates
from auto_report.settings import Settings


@dataclass(slots=True)
class SignalRecord:
    title: str
    url: str
    summary: str
    primary_domain: str
    matched_domains: list[str]
    score: float
    evidence_count: int
    tags: list[str]


@dataclass(slots=True)
class ReportPackage:
    signals: list[SignalRecord]
    summary_payload: dict[str, object]
    domain_payloads: dict[str, dict[str, object]]
    dedup_state: dict[str, object]


def _topic_summary(topic: TopicGroup) -> str:
    summaries = [item.summary.strip() for item in topic.evidence_items if item.summary.strip()]
    if summaries:
        return summaries[0]
    return f"来源共 {len(topic.evidence_items)} 条，等待后续 AI 深度摘要。"


def build_report_package(
    settings: Settings,
    items: list[CollectedItem],
    diagnostics: list[str],
) -> ReportPackage:
    topic_candidates = build_topic_candidates(items)
    topics = deduplicate_items(items)
    signals: list[SignalRecord] = []

    for topic in topics:
        domain_match = classify_topic(topic)
        tags = sorted({tag for item in topic.evidence_items for tag in item.tags if tag})
        signals.append(
            SignalRecord(
                title=topic.canonical_title,
                url=topic.canonical_url,
                summary=_topic_summary(topic),
                primary_domain=domain_match.primary_domain,
                matched_domains=domain_match.matched_domains,
                score=score_topic(topic),
                evidence_count=len(topic.evidence_items),
                tags=tags,
            )
        )

    signals.sort(key=lambda signal: signal.score, reverse=True)

    summary_payload = {
        "meta": {
            "generated_at": "",
            "timezone": settings.env["AUTO_TIMEZONE"],
            "total_items": len(items),
            "total_topics": len(topic_candidates),
        },
        "highlights": [
            f"本轮共采集到 {len(items)} 条原始信息，去重后保留 {len(signals)} 个主题。",
            f"当前覆盖 {len(settings.domains)} 个领域，启用了 {len(settings.sources)} 组来源配置。",
        ],
        "risks": diagnostics,
        "signals": [asdict(signal) for signal in signals],
        "predictions": [
            "热点主题会继续按跨源出现频次、关键词匹配和后续 AI 摘要结果动态调整。",
        ],
        "sources": settings.sources,
    }

    domain_payloads: dict[str, dict[str, object]] = {}
    for domain_key, domain in settings.domains.items():
        matched = [asdict(signal) for signal in signals if signal.primary_domain == domain_key]
        domain_payloads[domain_key] = {
            "title": domain.get("title", domain_key),
            "highlights": [
                f"本领域当前命中 {len(matched)} 个主题。",
            ],
            "signals": matched,
            "risks": diagnostics,
        }

    dedup_state = {
        "topics": [
            {
                "url": signal.url,
                "title": signal.title,
                "primary_domain": signal.primary_domain,
                "score": signal.score,
            }
            for signal in signals
        ]
    }

    return ReportPackage(
        signals=signals,
        summary_payload=summary_payload,
        domain_payloads=domain_payloads,
        dedup_state=dedup_state,
    )
