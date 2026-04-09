from __future__ import annotations

from dataclasses import asdict
import json

from auto_report.integrations.deepseek import summarize_with_deepseek
from auto_report.models.records import TopicCandidate

ANALYSIS_REQUIRED_KEYS = {"facts", "primary_contradiction", "core_insight", "confidence"}
SUMMARY_REQUIRED_KEYS = {
    "one_line_core",
    "executive_summary",
    "key_points",
    "key_insights",
    "limitations",
    "actions",
}
FORECAST_REQUIRED_KEYS = {
    "best_case",
    "worst_case",
    "most_likely_case",
    "key_variables",
    "forecast_conclusion",
    "confidence",
}


def _parse_json_block(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.removeprefix("```json").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```").strip()
    if cleaned.endswith("```"):
        cleaned = cleaned.removesuffix("```").strip()

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        raise ValueError("AI response must be a JSON object")
    return payload


def _unwrap_named_payload(payload: dict[str, object], stage: str) -> dict[str, object]:
    nested = payload.get(stage)
    if isinstance(nested, dict):
        return nested
    return payload


def _validate_required_keys(payload: dict[str, object], required_keys: set[str]) -> dict[str, object]:
    missing_keys = [key for key in required_keys if key not in payload]
    if missing_keys:
        raise ValueError(f"AI response missing required keys: {', '.join(sorted(missing_keys))}")
    return payload


def _build_analysis_prompt(reading: str, candidate: TopicCandidate) -> str:
    return "\n\n".join(
        [
            reading,
            "你正在自动情报快报流水线中工作。输入不是用户提问，而是系统已经筛选好的主题候选。",
            "任务：基于给定主题候选和证据片段，输出面向晨报编排的结构化分析。",
            "要求：不要索要补充信息；不要解释流程；不要输出 Markdown；只输出一个 JSON 对象。",
            '输出 JSON 字段必须包含：{"facts":["..."],"contradictions":["..."],"primary_contradiction":"...","core_insight":"...","confidence":"low|medium|high"}',
            "主题候选：",
            json.dumps(asdict(candidate), ensure_ascii=False, indent=2),
        ]
    )


def _build_summary_prompt(reading: str, analyses: list[dict[str, object]]) -> str:
    return "\n\n".join(
        [
            reading,
            "你正在自动情报快报流水线中工作。输入已经是完成初步分析的主题列表，不要回到信息充分性检测，不要索要额外背景。",
            "任务：把这些主题分析整理为晨报综合摘要。",
            "要求：不要复述输入结构；不要输出 analyses、analysis、summary 作为顶层键；只输出一个 JSON 对象。",
            '输出 JSON 字段必须包含：{"one_line_core":"...","executive_summary":["..."],"key_points":[{"title":"...","why_it_matters":"..."}],"key_insights":["..."],"limitations":["..."],"actions":["..."]}',
            "主题分析列表：",
            json.dumps(analyses, ensure_ascii=False, indent=2),
        ]
    )


def _build_forecast_prompt(
    reading: str,
    analyses: list[dict[str, object]],
    summary: dict[str, object],
) -> str:
    return "\n\n".join(
        [
            reading,
            "你正在自动情报快报流水线中工作。输入已经包含主题分析和综合摘要。",
            "任务：给出谨慎、可追溯的短期预测。",
            "要求：不要回显 analyses 或 summary 输入结构；不要索要补充信息；只输出一个 JSON 对象。",
            '输出 JSON 字段必须包含：{"best_case":"...","worst_case":"...","most_likely_case":"...","key_variables":["..."],"forecast_conclusion":"...","confidence":"low|medium|high"}',
            "输入：",
            json.dumps({"analyses": analyses, "summary": summary}, ensure_ascii=False, indent=2),
        ]
    )


def _fallback_analysis(candidate: TopicCandidate) -> dict[str, object]:
    return {
        "title": candidate.title,
        "url": candidate.url,
        "primary_domain": candidate.primary_domain,
        "facts": candidate.evidence_snippets or [f"Collected {candidate.evidence_count} evidence items"],
        "contradictions": ["signal strength vs evidence completeness"],
        "primary_contradiction": "signal strength vs evidence completeness",
        "core_insight": f"{candidate.title} is relevant but needs deeper verification.",
        "confidence": "low",
    }


def _fallback_summary(analyses: list[dict[str, object]]) -> dict[str, object]:
    titles = [str(item.get("title", "未命名主题")) for item in analyses[:3]]
    return {
        "one_line_core": "本轮先按规则模式输出，AI 总结阶段已回退。",
        "executive_summary": [f"重点关注：{title}" for title in titles] or ["暂无足够主题"],
        "key_points": [{"title": title, "why_it_matters": "需要继续观察。"} for title in titles],
        "key_insights": ["当前输出来自规则回退路径。"],
        "limitations": ["AI 总结阶段失败，请结合原始链接复核。"],
        "actions": ["优先检查来源页面与模型响应。"],
    }


def _fallback_forecast(summary: dict[str, object]) -> dict[str, object]:
    return {
        "best_case": "后续轮次恢复完整预测输出。",
        "worst_case": "本轮仅保留事实与总结，不输出可靠预测。",
        "most_likely_case": "近期继续观察主题是否形成跨源重复出现。",
        "key_variables": ["cross_source_repetition", "official_release_follow_up"],
        "forecast_conclusion": "本轮预测阶段已回退，暂不提供强结论。",
        "confidence": "low",
    }


def run_staged_ai_pipeline(
    candidates: list[TopicCandidate],
    ai_readings: dict[str, str],
    ai_enabled: bool,
    max_candidates: int | None = None,
) -> dict[str, object]:
    if max_candidates is not None and max_candidates > 0:
        selected_candidates = candidates[:max_candidates]
    else:
        selected_candidates = candidates

    analyses: list[dict[str, object]] = []
    stage_status = {"analysis": "skipped", "summary": "skipped", "forecast": "skipped"}

    if ai_enabled:
        try:
            for candidate in selected_candidates:
                prompt = _build_analysis_prompt(ai_readings["analysis"], candidate)
                analysis = _parse_json_block(summarize_with_deepseek(prompt))
                analysis = _unwrap_named_payload(analysis, "analysis")
                analysis = _validate_required_keys(analysis, ANALYSIS_REQUIRED_KEYS)
                analysis.setdefault("title", candidate.title)
                analysis.setdefault("url", candidate.url)
                analysis.setdefault("primary_domain", candidate.primary_domain)
                analyses.append(analysis)
            stage_status["analysis"] = "ok"
        except Exception:
            analyses = [_fallback_analysis(candidate) for candidate in selected_candidates]
            stage_status["analysis"] = "fallback"
    else:
        analyses = [_fallback_analysis(candidate) for candidate in selected_candidates]
        stage_status["analysis"] = "fallback"

    if ai_enabled and stage_status["analysis"] == "ok":
        try:
            prompt = _build_summary_prompt(ai_readings["summary"], analyses)
            summary = _parse_json_block(summarize_with_deepseek(prompt))
            summary = _unwrap_named_payload(summary, "summary")
            summary = _validate_required_keys(summary, SUMMARY_REQUIRED_KEYS)
            stage_status["summary"] = "ok"
        except Exception:
            summary = _fallback_summary(analyses)
            stage_status["summary"] = "fallback"
    else:
        summary = _fallback_summary(analyses)
        stage_status["summary"] = "fallback"

    if ai_enabled and stage_status["summary"] == "ok":
        try:
            prompt = _build_forecast_prompt(ai_readings["forecast"], analyses, summary)
            forecast = _parse_json_block(summarize_with_deepseek(prompt))
            forecast = _unwrap_named_payload(forecast, "forecast")
            forecast = _validate_required_keys(forecast, FORECAST_REQUIRED_KEYS)
            stage_status["forecast"] = "ok"
        except Exception:
            forecast = _fallback_forecast(summary)
            stage_status["forecast"] = "fallback"
    else:
        forecast = _fallback_forecast(summary)
        stage_status["forecast"] = "fallback"

    return {
        "analyses": analyses,
        "summary": summary,
        "forecast": forecast,
        "stage_status": stage_status,
    }
