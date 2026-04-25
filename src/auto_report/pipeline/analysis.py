from __future__ import annotations

from dataclasses import asdict, dataclass

from auto_report.domains.classifier import classify_topic
from auto_report.integrations.llm_client import is_llm_enabled
from auto_report.models.records import CollectedItem, TopicGroup
from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline
from auto_report.pipeline.dedup import deduplicate_items
from auto_report.pipeline.intelligence import apply_intelligence_layer, fetch_external_support_evidence
from auto_report.pipeline.prompt_loader import load_ai_readings
from auto_report.pipeline.scoring import score_topic
from auto_report.pipeline.topic_builder import build_topic_candidates
from auto_report.settings import Settings
from auto_report.source_registry import build_source_registry


RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


@dataclass(slots=True)
class SignalRecord:
    title: str
    url: str
    summary: str
    primary_domain: str
    matched_domains: list[str]
    score: float
    evidence_count: int
    source_ids: list[str]
    tags: list[str]


@dataclass(slots=True)
class ReportPackage:
    signals: list[SignalRecord]
    summary_payload: dict[str, object]
    domain_payloads: dict[str, dict[str, object]]
    dedup_state: dict[str, object]
    external_enrichment: dict[str, object]


def _default_ai_metrics() -> dict[str, object]:
    return {
        "provider": "",
        "model": "",
        "calls": 0,
        "token_usage": {
            "prompt": 0,
            "completion": 0,
            "total": 0,
        },
        "latency_seconds": 0.0,
        "fallback_stages": [],
        "backup_stages": [],
        "guardrail_stages": [],
    }


def _topic_summary(topic: TopicGroup) -> str:
    summaries = [item.summary.strip() for item in topic.evidence_items if item.summary.strip()]
    if summaries:
        return summaries[0]
    return f"来源共 {len(topic.evidence_items)} 条，等待后续 AI 深度摘要。"


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _comparison_source_ids(signal: dict[str, object]) -> list[str]:
    source_ids = signal.get("source_ids", [])
    if not isinstance(source_ids, list):
        return []
    return [str(source_id).strip() for source_id in source_ids if str(source_id).strip()]


def _comparison_signal_rows(
    signals: list[dict[str, object]],
    source_registry: dict[str, dict[str, object]],
) -> dict[str, dict[str, list[dict[str, object]]]]:
    rows: dict[str, dict[str, list[dict[str, object]]]] = {"cn": {}, "intl": {}}
    for signal in signals:
        title = str(signal.get("title", "")).strip()
        if not title:
            continue
        source_ids = _comparison_source_ids(signal)
        source_labels = [
            source_registry.get(source_id, {})
            for source_id in source_ids
            if isinstance(source_registry.get(source_id, {}), dict)
        ]
        regions = sorted(
            {
                str(label.get("region_scope", "")).strip()
                for label in source_labels
                if str(label.get("region_scope", "")).strip() in {"cn", "intl"}
            }
        )
        tracks = sorted(
            {
                str(label.get("tech_track", "")).strip()
                for label in source_labels
                if str(label.get("tech_track", "")).strip()
            }
        )
        if not regions or not tracks:
            continue
        for region in regions:
            for track in tracks:
                rows[region].setdefault(track, []).append(
                    {
                        "title": title,
                        "url": str(signal.get("url", "")).strip(),
                        "summary": str(signal.get("summary", "")).strip(),
                        "tech_track": track,
                        "source_ids": source_ids,
                        "score": _safe_float(signal.get("score", 0)),
                    }
                )
    return rows


def _sorted_comparison_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    unique: dict[tuple[str, str], dict[str, object]] = {}
    for item in items:
        key = (str(item.get("tech_track", "")), str(item.get("title", "")))
        unique.setdefault(key, item)
    return sorted(
        unique.values(),
        key=lambda item: (-_safe_float(item.get("score", 0)), str(item.get("tech_track", "")), str(item.get("title", ""))),
    )


def _flatten_comparison_region(region_rows: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for track_items in region_rows.values():
        items.extend(track_items)
    return _sorted_comparison_items(items)[:5]


def _build_comparison_brief(
    signals: list[dict[str, object]],
    source_registry: dict[str, dict[str, object]],
) -> dict[str, object]:
    rows = _comparison_signal_rows(signals, source_registry)
    cn_tracks = set(rows["cn"])
    intl_tracks = set(rows["intl"])
    head_to_head: list[dict[str, object]] = []

    for track in sorted(cn_tracks & intl_tracks):
        cn_item = _sorted_comparison_items(rows["cn"][track])[0]
        intl_item = _sorted_comparison_items(rows["intl"][track])[0]
        cn_title = str(cn_item.get("title", ""))
        intl_title = str(intl_item.get("title", ""))
        head_to_head.append(
            {
                "tech_track": track,
                "cn_title": cn_title,
                "intl_title": intl_title,
                "cn_source_ids": cn_item.get("source_ids", []),
                "intl_source_ids": intl_item.get("source_ids", []),
                "readout": f"{track}：国内 {cn_title}；海外 {intl_title}。",
            }
        )

    gaps = [
        f"{track}：仅看到国内信号，需补齐海外来源。"
        for track in sorted(cn_tracks - intl_tracks)
    ] + [
        f"{track}：仅看到海外信号，需补齐国内来源。"
        for track in sorted(intl_tracks - cn_tracks)
    ]

    watchpoints = [
        f"继续跟踪 {item['tech_track']} 的国内外同轨发布、生态采用与真实交付反馈。"
        for item in head_to_head[:3]
    ]
    if not watchpoints and gaps:
        watchpoints = ["优先补齐单侧覆盖赛道的对侧来源，再做趋势判断。"]

    return {
        "cn_highlights": _flatten_comparison_region(rows["cn"]),
        "intl_highlights": _flatten_comparison_region(rows["intl"]),
        "head_to_head": head_to_head,
        "gaps": gaps,
        "watchpoints": watchpoints,
    }


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
                source_ids=sorted({item.source_id for item in topic.evidence_items}),
                tags=tags,
            )
    )

    signals.sort(key=lambda signal: signal.score, reverse=True)
    signal_scores = {(signal.title, signal.url): signal.score for signal in signals}
    topic_candidates.sort(
        key=lambda candidate: signal_scores.get((candidate.title, candidate.url), 0.0),
        reverse=True,
    )

    ai_outputs = run_staged_ai_pipeline(
        candidates=topic_candidates,
        ai_readings=load_ai_readings(settings.root_dir),
        ai_enabled=is_llm_enabled(),
        max_candidates=int(settings.env["AI_MAX_ANALYSIS_TOPICS"]),
    )

    enriched_signals = [asdict(signal) for signal in signals]
    external_enrichment_fetcher = None
    external_enrichment_max_signals = int(settings.env.get("EXTERNAL_ENRICHMENT_MAX_SIGNALS", "2"))
    if settings.env.get("EXTERNAL_ENRICHMENT_ENABLED", "false").lower() == "true":
        timeout_seconds = int(settings.env.get("EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS", "8"))

        def external_enrichment_fetcher(root_dir, signal):
            return fetch_external_support_evidence(root_dir, signal, timeout_seconds=timeout_seconds)

    intelligence = apply_intelligence_layer(
        root_dir=settings.root_dir,
        signals=enriched_signals,
        analyses=ai_outputs["analyses"],
        items=items,
        diagnostics=diagnostics,
        external_enrichment_fetcher=external_enrichment_fetcher,
        external_enrichment_max_signals=external_enrichment_max_signals,
    )

    risk_level = intelligence["risk_level"]
    if any(status == "fallback" for status in ai_outputs["stage_status"].values()):
        stage_risk = "high" if ai_outputs["stage_status"].get("analysis") == "fallback" else "medium"
        risk_level = max((risk_level, stage_risk), key=lambda item: RISK_ORDER.get(item, -1))

    comparison_brief = _build_comparison_brief(
        signals=intelligence["signals"],
        source_registry=build_source_registry(settings),
    )

    summary_payload = {
        "meta": {
            "generated_at": "",
            "timezone": settings.env["AUTO_TIMEZONE"],
            "total_items": len(items),
            "total_topics": len(topic_candidates),
        },
        "one_line_core": ai_outputs["summary"]["one_line_core"],
        "executive_summary": ai_outputs["summary"]["executive_summary"],
        "key_points": ai_outputs["summary"]["key_points"],
        "key_insights": ai_outputs["summary"]["key_insights"],
        "limitations": list(ai_outputs["summary"].get("limitations", [])),
        "actions": ai_outputs["summary"]["actions"],
        "analyses": intelligence["analyses"],
        "forecast": ai_outputs["forecast"],
        "stage_status": ai_outputs["stage_status"],
        "ai_metrics": ai_outputs.get("ai_metrics", _default_ai_metrics()),
        "mainline_memory": intelligence["mainline_memory"],
        "lifecycle_summary": intelligence["lifecycle_summary"],
        "comparison_brief": comparison_brief,
        "risk_level": risk_level,
        "highlights": [
            ai_outputs["summary"]["one_line_core"],
            f"本轮共采集到 {len(items)} 条原始信息，去重后保留 {len(signals)} 个主题。",
            f"当前覆盖 {len(settings.domains)} 个领域，启用了 {len(settings.sources)} 组来源配置。",
        ],
        "risks": diagnostics,
        "signals": intelligence["signals"],
        "predictions": [str(ai_outputs["forecast"].get("forecast_conclusion", "暂无趋势提示"))],
        "sources": settings.sources,
    }

    domain_payloads: dict[str, dict[str, object]] = {}
    for domain_key, domain in settings.domains.items():
        matched = [signal for signal in intelligence["signals"] if signal.get("primary_domain") == domain_key]
        matched_analyses = [
            analysis
            for analysis in intelligence["analyses"]
            if analysis.get("primary_domain") == domain_key
        ]
        domain_payloads[domain_key] = {
            "title": domain.get("title", domain_key),
            "one_line_core": summary_payload["one_line_core"],
            "executive_summary": [f"本领域当前命中 {len(matched)} 个主题。"],
            "key_points": [
                {
                    "title": str(analysis.get("title", "未命名主题")),
                    "why_it_matters": str(analysis.get("core_insight", "需要继续观察。")),
                }
                for analysis in matched_analyses[:2]
            ],
            "key_insights": [
                str(analysis.get("core_insight", "需要继续观察。"))
                for analysis in matched_analyses[:3]
            ],
            "limitations": summary_payload["limitations"],
            "actions": summary_payload["actions"],
            "analyses": matched_analyses,
            "forecast": summary_payload["forecast"],
            "highlights": [f"本领域当前命中 {len(matched)} 个主题。"],
            "signals": matched,
            "risks": diagnostics,
            "predictions": summary_payload["predictions"],
            "risk_level": risk_level,
        }

    dedup_state = {
        "topics": [
            {
                "url": signal["url"],
                "title": signal["title"],
                "primary_domain": signal["primary_domain"],
                "score": signal["score"],
                "lifecycle_state": signal.get("lifecycle_state", "new"),
                "risk_level": signal.get("risk_level", "low"),
            }
            for signal in intelligence["signals"]
        ]
    }

    return ReportPackage(
        signals=signals,
        summary_payload=summary_payload,
        domain_payloads=domain_payloads,
        dedup_state=dedup_state,
        external_enrichment=intelligence.get("external_enrichment", {}),
    )
