from __future__ import annotations
import math

from auto_report.models.records import TopicGroup


HIGH_SIGNAL_KEYWORDS = (
    "agent", "llm", "npu", "accelerator", "on-device",
    "edge ai", "inference engine", "model optimization",
)
MEDIUM_SIGNAL_KEYWORDS = (
    "open source", "release", "benchmark", "framework",
    "deployment", "embedded", "microcontroller",
)

# Source type categories for cross-source diversity scoring
_SOURCE_TYPE_MAP: dict[str, str] = {
    # RSS sources -> "rss"
    "huggingface-blog": "rss", "openai-news": "rss",
    "google-deepmind-blog": "rss", "meta-ai-blog": "rss",
    "microsoft-research": "rss",
    # GitHub sources -> "github"
    "curated-agent-repos": "github", "curated-edge-repos": "github",
    "curated-infra-repos": "github",
    # Website sources -> "web"
    "anthropic-news": "web", "deepseek-updates": "web",
    "qwen-blog": "web", "moonshot-blog": "web",
    "arm-news": "web", "qualcomm-onq": "web",
    "nvidia-embedded": "web", "google-ai-edge": "web",
    "openvino-blog": "web", "st-blog": "web",
    "infineon-blog": "web", "ti-e2e-blog": "web",
}


def _count_source_types(topic: TopicGroup) -> int:
    """Count distinct source type categories among evidence items."""
    types: set[str] = set()
    for item in topic.evidence_items:
        stype = _SOURCE_TYPE_MAP.get(item.source_id, item.source_id.split("-")[0])
        types.add(stype)
    return len(types)


def _has_summary_evidence(topic: TopicGroup) -> int:
    """Count how many evidence items have non-empty summaries."""
    return sum(1 for item in topic.evidence_items if item.summary.strip())


def score_topic(topic: TopicGroup) -> float:
    evidence_count = len(topic.evidence_items)
    title = topic.canonical_title.lower()

    # Keyword signal tiers
    high_signal = 1.5 if any(t in title for t in HIGH_SIGNAL_KEYWORDS) else 0.0
    medium_signal = 0.8 if any(t in title for t in MEDIUM_SIGNAL_KEYWORDS) else 0.0

    # Cross-source diversity: reward topics confirmed by different source TYPES
    source_type_count = _count_source_types(topic)
    diversity_bonus = math.log2(max(source_type_count, 1)) * 1.2

    # Evidence quality: prefer topics with actual summary text vs empty
    summary_ratio = _has_summary_evidence(topic) / max(evidence_count, 1)
    quality_weight = 0.3 + (summary_ratio * 0.7)

    base_score = evidence_count * quality_weight
    return round(base_score + diversity_bonus + high_signal + medium_signal, 2)
