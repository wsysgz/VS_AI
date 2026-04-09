from auto_report.models.records import CollectedItem
from auto_report.pipeline.topic_builder import build_topic_candidates


def test_build_topic_candidates_merges_source_ids_and_summaries():
    items = [
        CollectedItem(
            source_id="openai-news",
            item_id="1",
            title="OpenAI launches feature",
            url="https://example.com/feature",
            summary="OpenAI launched feature A",
            published_at="2026-04-10T00:00:00+00:00",
            collected_at="2026-04-10T00:01:00+00:00",
            tags=["ai-llm-agent"],
            language="en",
            metadata={},
        ),
        CollectedItem(
            source_id="anthropic-news",
            item_id="2",
            title="OpenAI launches feature",
            url="https://example.com/feature",
            summary="Independent confirmation of feature A",
            published_at="2026-04-10T00:02:00+00:00",
            collected_at="2026-04-10T00:03:00+00:00",
            tags=["ai-llm-agent"],
            language="en",
            metadata={},
        ),
    ]

    candidates = build_topic_candidates(items)

    assert len(candidates) == 1
    assert candidates[0].evidence_count == 2
    assert candidates[0].source_ids == ["anthropic-news", "openai-news"]
    assert "OpenAI launched feature A" in candidates[0].evidence_snippets
