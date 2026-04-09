from auto_report.domains.classifier import classify_topic
from auto_report.models.records import CollectedItem
from auto_report.pipeline.dedup import deduplicate_items


def test_classify_topic_prefers_ai_x_electronics_for_npu_signal():
    item = CollectedItem(
        source_id="rss",
        item_id="1",
        title="New edge AI NPU launch",
        url="https://example.com/npu",
        summary="Embedded accelerator for edge AI cameras",
        published_at="2026-04-09T00:00:00+00:00",
        collected_at="2026-04-09T01:00:00+00:00",
        tags=["edge ai", "npu"],
        language="en",
        metadata={},
    )

    topic = deduplicate_items([item])[0]
    result = classify_topic(topic)

    assert result.primary_domain == "ai-x-electronics"
