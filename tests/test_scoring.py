from auto_report.models.records import CollectedItem, TopicGroup
from auto_report.pipeline.scoring import _count_source_types


def _item(source_id: str) -> CollectedItem:
    return CollectedItem(
        source_id=source_id,
        item_id=source_id,
        title=f"{source_id} headline",
        url=f"https://example.com/{source_id}",
        summary="official source summary",
        published_at="2026-04-28T00:00:00+00:00",
        collected_at="2026-04-28T00:00:00+00:00",
        tags=["ai-x-electronics"],
        language="zh",
        metadata={},
    )


def test_count_source_types_treats_validated_domestic_listing_sources_as_web():
    topic = TopicGroup(
        group_id="topic-1",
        canonical_title="Domestic edge AI coverage",
        canonical_url="https://example.com/topic",
        evidence_items=[
            _item("cambricon-dev-news"),
            _item("sophgo-news"),
            _item("horizon-product-news"),
            _item("rockchip-news"),
        ],
    )

    assert _count_source_types(topic) == 1
