from __future__ import annotations

from dataclasses import asdict
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from auto_report.integrations.llm_client import call_llm as summarize_with_deepseek
from auto_report.models.records import TopicCandidate

logger = logging.getLogger(__name__)

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
    evidence_count = candidate.evidence_count
    source_ids = candidate.source_ids
    sources_joined = ", ".join(source_ids[:4]) if source_ids else "unknown"
    snippets_preview = (
        candidate.evidence_snippets[0][:120] if candidate.evidence_snippets
        else f"Collected {evidence_count} evidence items (no text summary available)"
    )
    return {
        "title": candidate.title,
        "url": candidate.url,
        "primary_domain": candidate.primary_domain,
        "facts": [snippets_preview] if snippets_preview else [f"Collected {evidence_count} raw items from {sources_joined}"],
        "contradictions": ["insufficient evidence depth for contradiction detection"],
        "primary_contradiction": f"signal visibility vs evidence depth (evidence={evidence_count}, sources={len(source_ids)})",
        "core_insight": (
            f"{candidate.title} appeared across {len(source_ids)} source(s) with {evidence_count} item(s). "
            "Requires deeper verification and AI-assisted analysis."
        ),
        "confidence": "low" if evidence_count <= 1 else "medium",
        "source_count": len(source_ids),
    }


def _fallback_summary(analyses: list[dict[str, object]]) -> dict[str, object]:
    titles = [str(item.get("title", "未命名主题")) for item in analyses[:3]]
    total_sources: set[str] = set()
    confidences: list[str] = []
    for a in analyses:
        for s in a.get("source_ids", []):
            total_sources.add(s)
        confidences.append(str(a.get("confidence", "low")))

    high_conf_count = sum(1 for c in confidences if c == "high")
    med_count = sum(1 for c in confidences if c == "medium")

    return {
        "one_line_core": f"本轮采集到 {len(analyses)} 个主题，覆盖 {len(total_sources)} 个信息源（{high_conf_count}高置信/{med_count}中置信）。",
        "executive_summary": [
            f"重点关注：{title}" if i == 0 else title
            for i, title in enumerate(titles)
        ] or ["暂无足够主题"],
        "key_points": [
            {"title": title, "why_it_matters": str(a.get("core_insight", "需要继续观察。"))}
            for title, a in zip(titles, analyses[:3])
        ],
        "key_insights": [
            str(a.get("core_insight", "需要继续观察。")) for a in analyses[:3]
        ] or ["当前输出来自规则回退路径。"],
        "limitations": [
            "AI 总结阶段失败或被跳过，以下为规则引擎生成的摘要。",
            "建议检查 DeepSeek API 配置和网络连通性。",
        ],
        "actions": ["优先检查来源页面与模型响应。", "确认 API Key 有效性后重试以获得 AI 增强分析。"],
    }


def _fallback_forecast(summary: dict[str, object]) -> dict[str, object]:
    exec_summary = summary.get("executive_summary", [])
    top_focus = str(exec_summary[0]).replace("重点关注：", "") if exec_summary else "未知主题"
    return {
        "best_case": f"若 {top_focus} 持续获得跨源验证，可能成为近期重要趋势信号。",
        "worst_case": f"若 {top_focus} 仅为单次出现，后续可能不再重复，需持续观察确认。",
        "most_likely_case": (
            f"{top_focus} 等主题将在未来数天内继续出现在多个信息源中，"
            "建议保持监控并关注官方后续发布。"
        ),
        "key_variables": [
            "cross_source_repetition",
            "official_release_follow_up",
            "community_adoption_signal",
        ],
        "forecast_conclusion": "本轮预测阶段已回退（无AI分析），结论基于规则模式匹配。启用 DeepSeek API 可获得更精准预测。",
        "confidence": "low",
    }


def _analyze_single_candidate(
    candidate: TopicCandidate,
    ai_readings: dict[str, str],
) -> dict[str, object]:
    """单个候选的 AI 分析（线程安全，可被并发调用）"""
    prompt = _build_analysis_prompt(ai_readings["analysis"], candidate)
    raw = summarize_with_deepseek(prompt)
    parsed = _parse_json_block(raw)
    parsed = _unwrap_named_payload(parsed, "analysis")
    parsed = _validate_required_keys(parsed, ANALYSIS_REQUIRED_KEYS)
    parsed.setdefault("title", candidate.title)
    parsed.setdefault("url", candidate.url)
    parsed.setdefault("primary_domain", candidate.primary_domain)
    return parsed


def run_staged_ai_pipeline(
    candidates: list[TopicCandidate],
    ai_readings: dict[str, str],
    ai_enabled: bool,
    max_candidates: int | None = None,
    enable_pre_filter: bool = True,
) -> dict[str, object]:
    if max_candidates is not None and max_candidates > 0:
        selected_candidates = candidates[:max_candidates]
    else:
        selected_candidates = candidates

    analyses: list[dict[str, object]] = []
    low_score_analyses: list[dict[str, object]] = []
    stage_status = {"analysis": "skipped", "summary": "skipped", "forecast": "skipped"}

    if ai_enabled:
        # ═══ Phase 1.3: AI 预筛选（可选）═══
        if enable_pre_filter and len(selected_candidates) > 3:
            try:
                from auto_report.pipeline.scoring_llm import apply_pre_filter

                high_score, low_score = apply_pre_filter(selected_candidates, ai_readings)
                selected_candidates = high_score
                if low_score:
                    low_score_analyses = [_fallback_analysis(c) for c in low_score]
                    logger.info(
                        "Pre-filter applied: %d high-score + %d low-score(fallback)",
                        len(high_score),
                        len(low_score),
                    )
            except Exception as exc:
                logger.warning("Pre-filter failed (%s), analyzing all %d candidates", exc, len(selected_candidates))

        # 确保至少有候选可分析
        if not selected_candidates:
            selected_candidates = candidates[:max_candidates] if max_candidates else candidates
            logger.warning("All candidates filtered out by pre-score, falling back to original list")

        # ═══ Phase 1.1: 并行 Analysis ═══
        max_workers = min(len(selected_candidates), 5)  # 最多5路并发

        try:
            analyses = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_candidate = {
                    executor.submit(_analyze_single_candidate, c, ai_readings): c
                    for c in selected_candidates
                }
                for future in as_completed(future_to_candidate):
                    candidate = future_to_candidate[future]
                    try:
                        analysis = future.result(timeout=60)  # 单个超时60s
                        analyses.append(analysis)
                    except Exception as exc:
                        logger.warning("Analysis failed for %s: %s", candidate.title, exc)
                        analyses.append(_fallback_analysis(candidate))

            stage_status["analysis"] = "ok"
            logger.info("Parallel analysis complete: %d/%d candidates analyzed", len(analyses), len(selected_candidates))
        except Exception as exc:
            logger.error("Parallel analysis batch failed: %s, falling back", exc)
            analyses = [_fallback_analysis(candidate) for candidate in selected_candidates]
            stage_status["analysis"] = "fallback"
    else:
        analyses = [_fallback_analysis(candidate) for candidate in selected_candidates]
        stage_status["analysis"] = "fallback"

    # 合并高分分析结果和低分 fallback 结果（低分的排在后面）
    all_analyses = analyses + low_score_analyses

    if ai_enabled and stage_status["analysis"] == "ok":
        try:
            prompt = _build_summary_prompt(ai_readings["summary"], all_analyses)
            summary = _parse_json_block(summarize_with_deepseek(prompt))
            summary = _unwrap_named_payload(summary, "summary")
            summary = _validate_required_keys(summary, SUMMARY_REQUIRED_KEYS)
            stage_status["summary"] = "ok"
        except Exception:
            summary = _fallback_summary(all_analyses)
            stage_status["summary"] = "fallback"
    else:
        summary = _fallback_summary(all_analyses)
        stage_status["summary"] = "fallback"

    if ai_enabled and stage_status["summary"] == "ok":
        try:
            prompt = _build_forecast_prompt(ai_readings["forecast"], all_analyses, summary)
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
        "analyses": all_analyses,
        "summary": summary,
        "forecast": forecast,
        "stage_status": stage_status,
    }
