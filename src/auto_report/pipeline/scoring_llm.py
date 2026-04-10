"""AI 驱动的预筛选模块 — 在深度分析前批量打分过滤低质量候选主题

参考: Horizon 的 Score + Filter 设计
原理: 用一次轻量 LLM 调用对所有候选主题打分(0-10)，低于阈值者跳过 AI 深度分析
收益: 减少 40-60% 的 token 消耗和 Analysis 调用次数
"""

from __future__ import annotations

import json
import logging

from auto_report.integrations.llm_client import call_llm as summarize_with_deepseek
from auto_report.models.records import TopicCandidate
from auto_report.pipeline.ai_pipeline import _fallback_analysis, _parse_json_block

logger = logging.getLogger(__name__)

# 默认阈值：低于此分数的主题不进入深度 AI 分析（走 fallback）
DEFAULT_SCORE_THRESHOLD = 5.0


def batch_score_candidates(
    candidates: list[TopicCandidate],
    ai_readings: dict[str, str],
) -> list[tuple[TopicCandidate, float]]:
    """对候选主题批量 LLM 打分
    
    Args:
        candidates: 候选主题列表
        ai_readings: AI prompt 字典（使用 analysis reading 作为系统提示前缀）
    
    Returns:
        [(candidate, score)] 列表，按分数降序排列
    """
    if not candidates:
        return []

    # 构建精简的评分 prompt
    payload = [
        {
            "title": c.title,
            "evidence_count": c.evidence_count,
            "source_count": len(c.source_ids),
            "sources": list(c.source_ids)[:4],
        }
        for c in candidates
    ]

    prompt = f"""你是一个科技情报质量评估器。对以下 {len(candidates)} 个情报候选主题打分(0-10分)。

评分标准：
- 技术深度(30%)：是否涉及实质性技术进展(新模型/架构/突破)而非泛泛而谈
- 新颖性(30%)：是否提供全新信息还是已知内容的重复报道
- 影响力(25%)：对行业/领域/开发者社区的潜在影响程度
- 信息充分性(15%)：跨源佐证数量、证据质量

严格要求：大部分普通新闻应该在 3-6 分。只有真正重要的信号才给 7+ 分。不要慷慨。
输出纯 JSON 数组，不要任何其他文字：[{{"index":0, "score":7.5, "reason":"简短理由"}}]

候选主题列表：
{json.dumps(payload, ensure_ascii=False, indent=2)}
"""

    try:
        raw = summarize_with_deepseek(prompt)
        result = _parse_json_block(raw)

        scores: dict[int, float] = {}
        for item in result:
            idx = int(item.get("index", -1))
            if idx >= 0:
                scores[idx] = float(item.get("score", 3.0))

        scored = []
        for i, c in enumerate(candidates):
            s = scores.get(i, 3.0)  # 未匹配到的默认低分
            scored.append((c, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info("LLM scoring complete: %d candidates scored", len(scored))
        return scored

    except Exception as exc:
        logger.warning("LLM pre-scoring failed (%s), returning default scores", exc)
        # 打分失败时全部返回中等分数，让后续流程正常走 AI 分析
        return [(c, 6.0) for c in candidates]


def apply_pre_filter(
    candidates: list[TopicCandidate],
    ai_readings: dict[str, str],
    threshold: float = DEFAULT_SCORE_THRESHOLD,
    min_candidates_for_filter: int = 3,
) -> tuple[list[TopicCandidate], list[TopicCandidate]]:
    """应用预筛选：将候选分为高分组（进 AI 分析）和低分组（走 fallback）
    
    Args:
        candidates: 原始候选列表
        ai_readings: AI prompts
        threshold: 分数阈值，>= 进入深度分析
        min_candidates_for_filter: 少于等于此数量时跳过筛选（筛选本身有开销）
    
    Returns:
        (high_score_candidates, low_score_candidates) 元组
    """
    # 候选太少时不值得额外一次 LLM 调用来筛选
    if len(candidates) <= min_candidates_for_filter:
        logger.info(
            "Only %d candidates (<= %d), skipping pre-filter",
            len(candidates),
            min_candidates_for_filter,
        )
        return candidates, []

    try:
        scored = batch_score_candidates(candidates, ai_readings)
        high = [c for c, s in scored if s >= threshold]
        low = [c for c, s in scored if s < threshold]

        logger.info(
            "Pre-filter: %d total -> %d high-score(>=%.1f) + %d low-score -> ~%d%% fewer AI calls",
            len(candidates),
            len(high),
            threshold,
            len(low),
            (1 - len(high) / len(candidates)) * 100 if candidates else 0,
        )

        # 确保至少保留 top 3（防止阈值设置过高导致全被过滤）
        if len(high) < 3 and low:
            extra = sorted(
                [(c, s) for c, s in scored if c in low],
                key=lambda x: x[1],
                reverse=True,
            )[: 3 - len(high)]
            high.extend([c for c, s in extra])
            low = [c for c in low if c not in high]

        return high, low

    except Exception as exc:
        logger.error("Pre-filter failed, passing all candidates through: %s", exc)
        return candidates, []
