from auto_report.models.records import TopicCandidate
from auto_report.pipeline.scoring_llm import batch_score_candidates


def test_batch_score_candidates_accepts_json_array(monkeypatch):
    candidates = [
        TopicCandidate(
            topic_id="topic-1",
            title="Topic 1",
            url="https://example.com/1",
            primary_domain="ai-llm-agent",
            matched_domains=["ai-llm-agent"],
            evidence_count=1,
            source_ids=["rss"],
            tags=["agent"],
            evidence_snippets=["Snippet 1"],
        ),
        TopicCandidate(
            topic_id="topic-2",
            title="Topic 2",
            url="https://example.com/2",
            primary_domain="ai-llm-agent",
            matched_domains=["ai-llm-agent"],
            evidence_count=2,
            source_ids=["github"],
            tags=["benchmark"],
            evidence_snippets=["Snippet 2"],
        ),
    ]

    monkeypatch.setattr(
        "auto_report.pipeline.scoring_llm.summarize_with_deepseek",
        lambda prompt: '[{"index": 1, "score": 8.5}, {"index": 0, "score": 3.0}]',
    )

    scored = batch_score_candidates(candidates, {"analysis": "analysis-rules"})

    assert scored == [
        (candidates[1], 8.5),
        (candidates[0], 3.0),
    ]
