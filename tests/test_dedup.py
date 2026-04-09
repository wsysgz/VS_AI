from auto_report.models.records import CollectedItem
from auto_report.pipeline.dedup import deduplicate_items


def test_deduplicate_merges_same_url_items():
    first = CollectedItem(
        source_id="rss",
        item_id="1",
        title="Agent release",
        url="https://example.com/a",
        summary="first summary",
        published_at="2026-04-09T00:00:00+00:00",
        collected_at="2026-04-09T01:00:00+00:00",
        tags=["agent"],
        language="en",
        metadata={},
    )
    second = CollectedItem(
        source_id="web",
        item_id="2",
        title="Agent release updated",
        url="https://example.com/a",
        summary="second summary",
        published_at="2026-04-09T00:05:00+00:00",
        collected_at="2026-04-09T01:05:00+00:00",
        tags=["agent"],
        language="en",
        metadata={},
    )

    groups = deduplicate_items([first, second])

    assert len(groups) == 1
    assert len(groups[0].evidence_items) == 2
