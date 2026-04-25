from __future__ import annotations


def _pick_judgment(payload: dict[str, object]) -> str:
    return str(payload.get("one_line_core") or "").strip() or "暂无核心判断"


def _build_mainlines(payload: dict[str, object]) -> list[dict[str, str]]:
    lines: list[dict[str, str]] = []
    for point in payload.get("key_points", [])[:3]:
        title = str(point.get("title", "")).strip()
        why_it_matters = str(point.get("why_it_matters", "")).strip()
        if title:
            lines.append(
                {
                    "title": title,
                    "why_it_matters": why_it_matters or "需要继续观察",
                }
            )
    return lines


def _build_topic_briefs(payload: dict[str, object]) -> list[dict[str, str]]:
    briefs: list[dict[str, str]] = []
    for analysis in payload.get("analyses", [])[:3]:
        title = str(analysis.get("title", "")).strip()
        if not title:
            continue
        briefs.append(
            {
                "title": title,
                "primary_domain": str(analysis.get("primary_domain", "unknown")).strip() or "unknown",
                "core_insight": str(analysis.get("core_insight", "需要继续观察。")).strip() or "需要继续观察。",
                "primary_contradiction": str(analysis.get("primary_contradiction", "待补充")).strip() or "待补充",
                "confidence": str(analysis.get("confidence", "low")).strip() or "low",
                "url": str(analysis.get("url", "")).strip(),
                "lifecycle_state": str(analysis.get("lifecycle_state", "new")).strip() or "new",
                "risk_level": str(analysis.get("risk_level", "low")).strip() or "low",
                "enrichment_summary": str(
                    (analysis.get("enrichment") or {}).get("summary", "")
                ).strip(),
                "support_evidence": [
                    {
                        "source_type": str(item.get("source_type", "")).strip(),
                        "title": str(item.get("title", "")).strip(),
                        "url": str(item.get("url", "")).strip(),
                    }
                    for item in analysis.get("support_evidence", [])[:3]
                    if str(item.get("title", "")).strip()
                ],
            }
        )
    return briefs


def _build_mainline_memory(payload: dict[str, object]) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []
    for item in payload.get("mainline_memory", [])[:5]:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        lines.append(
            {
                "title": title,
                "lifecycle_state": str(item.get("lifecycle_state", "new")).strip() or "new",
                "risk_level": str(item.get("risk_level", "low")).strip() or "low",
                "days_seen": int(item.get("days_seen", 1)),
                "first_seen": str(item.get("first_seen", "")).strip(),
                "last_seen": str(item.get("last_seen", "")).strip(),
                "enrichment_summary": str(item.get("enrichment_summary", "")).strip(),
            }
        )
    return lines


def _comparison_empty() -> dict[str, list[object]]:
    return {
        "cn_highlights": [],
        "intl_highlights": [],
        "head_to_head": [],
        "gaps": [],
        "watchpoints": [],
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _comparison_highlights(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    highlights: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        source_ids = item.get("source_ids", [])
        if not isinstance(source_ids, list):
            source_ids = []
        highlights.append(
            {
                "title": title,
                "tech_track": str(item.get("tech_track", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "source_ids": [str(source_id).strip() for source_id in source_ids if str(source_id).strip()],
            }
        )
    return highlights


def _comparison_head_to_head(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        tech_track = str(item.get("tech_track", "")).strip()
        cn_title = str(item.get("cn_title", "")).strip()
        intl_title = str(item.get("intl_title", "")).strip()
        readout = str(item.get("readout", "")).strip()
        if not readout and tech_track and (cn_title or intl_title):
            readout = f"{tech_track}：国内 {cn_title or '暂无'}；海外 {intl_title or '暂无'}。"
        if not readout:
            continue
        rows.append(
            {
                "tech_track": tech_track,
                "cn_title": cn_title,
                "intl_title": intl_title,
                "readout": readout,
            }
        )
    return rows


def _build_comparison_brief(payload: dict[str, object]) -> dict[str, object]:
    raw = payload.get("comparison_brief", {})
    if not isinstance(raw, dict):
        return _comparison_empty()
    return {
        "cn_highlights": _comparison_highlights(raw.get("cn_highlights", [])),
        "intl_highlights": _comparison_highlights(raw.get("intl_highlights", [])),
        "head_to_head": _comparison_head_to_head(raw.get("head_to_head", [])),
        "gaps": _string_list(raw.get("gaps", [])),
        "watchpoints": _string_list(raw.get("watchpoints", [])),
    }


def compose_executive_brief(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> dict[str, object]:
    limitations = [str(item).strip() for item in payload.get("limitations", []) if str(item).strip()]
    actions = [str(item).strip() for item in payload.get("actions", []) if str(item).strip()]
    forecast = payload.get("forecast", {})
    comparison_brief = _build_comparison_brief(payload)

    return {
        "title": title,
        "generated_at": generated_at,
        "judgment": _pick_judgment(payload),
        "executive_summary": [
            str(item).strip()
            for item in payload.get("executive_summary", [])
            if str(item).strip()
        ],
        "key_insights": [
            str(item).strip()
            for item in payload.get("key_insights", [])
            if str(item).strip()
        ],
        "mainlines": _build_mainlines(payload),
        "mainline_memory": _build_mainline_memory(payload),
        "topic_briefs": _build_topic_briefs(payload),
        "watchlist": str(forecast.get("most_likely_case", "")).strip() or "本轮先保持观察，等待更多高置信度信号。",
        "forecast_conclusion": str(forecast.get("forecast_conclusion", "")).strip(),
        "risk_note": limitations[0] if limitations else "",
        "action_note": actions[0] if actions else "",
        "risk_level": str(payload.get("risk_level", "low")).strip() or "low",
        "comparison_brief": comparison_brief,
        "comparison_head_to_head": [
            str(item.get("readout", "")).strip()
            for item in comparison_brief["head_to_head"][:2]
            if str(item.get("readout", "")).strip()
        ],
        "limitations": limitations,
        "actions": actions,
        "stage_status": payload.get("stage_status", {}),
        "meta": payload.get("meta", {}),
    }
