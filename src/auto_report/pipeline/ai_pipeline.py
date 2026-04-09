from __future__ import annotations

from dataclasses import asdict
import json

from auto_report.integrations.deepseek import summarize_with_deepseek
from auto_report.models.records import TopicCandidate


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
) -> dict[str, object]:
    analyses: list[dict[str, object]] = []
    stage_status = {"analysis": "skipped", "summary": "skipped", "forecast": "skipped"}

    if ai_enabled:
        try:
            for candidate in candidates:
                prompt = "\n\n".join(
                    [
                        ai_readings["analysis"],
                        json.dumps(asdict(candidate), ensure_ascii=False, indent=2),
                        "请仅输出 JSON 对象。",
                    ]
                )
                analysis = _parse_json_block(summarize_with_deepseek(prompt))
                analysis.setdefault("title", candidate.title)
                analysis.setdefault("url", candidate.url)
                analysis.setdefault("primary_domain", candidate.primary_domain)
                analyses.append(analysis)
            stage_status["analysis"] = "ok"
        except Exception:
            analyses = [_fallback_analysis(candidate) for candidate in candidates]
            stage_status["analysis"] = "fallback"
    else:
        analyses = [_fallback_analysis(candidate) for candidate in candidates]
        stage_status["analysis"] = "fallback"

    if ai_enabled and stage_status["analysis"] == "ok":
        try:
            prompt = "\n\n".join(
                [
                    ai_readings["summary"],
                    json.dumps(analyses, ensure_ascii=False, indent=2),
                    "请仅输出 JSON 对象。",
                ]
            )
            summary = _parse_json_block(summarize_with_deepseek(prompt))
            stage_status["summary"] = "ok"
        except Exception:
            summary = _fallback_summary(analyses)
            stage_status["summary"] = "fallback"
    else:
        summary = _fallback_summary(analyses)
        stage_status["summary"] = "fallback"

    if ai_enabled and stage_status["summary"] == "ok":
        try:
            prompt = "\n\n".join(
                [
                    ai_readings["forecast"],
                    json.dumps({"analyses": analyses, "summary": summary}, ensure_ascii=False, indent=2),
                    "请仅输出 JSON 对象。",
                ]
            )
            forecast = _parse_json_block(summarize_with_deepseek(prompt))
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
