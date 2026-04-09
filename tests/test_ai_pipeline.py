from auto_report.models.records import TopicCandidate
from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline


def test_run_staged_ai_pipeline_returns_structured_outputs(monkeypatch):
    candidate = TopicCandidate(
        topic_id="topic-1",
        title="Agent benchmark release",
        url="https://example.com/agent",
        primary_domain="ai-llm-agent",
        matched_domains=["ai-llm-agent"],
        evidence_count=2,
        source_ids=["openai-news", "anthropic-news"],
        tags=["agent", "benchmark"],
        evidence_snippets=["Release notes", "Independent commentary"],
    )

    responses = iter(
        [
            '{"facts":["Release published"],"contradictions":["speed vs reliability"],"primary_contradiction":"speed vs reliability","core_insight":"evaluation is becoming central","confidence":"medium"}',
            '{"one_line_core":"Agent evaluation becomes a core battleground","executive_summary":["A","B"],"key_points":[{"title":"Signal","why_it_matters":"Matters"}],"key_insights":["Insight"],"limitations":["Need verification"],"actions":["Track benchmarks"]}',
            '{"most_likely_case":"benchmark competition intensifies","best_case":"better reliability","worst_case":"benchmark theater","key_variables":["real deployment"],"forecast_conclusion":"watch evaluation quality","confidence":"medium"}',
        ]
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.summarize_with_deepseek",
        lambda prompt: next(responses),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "ok"
    assert outputs["summary"]["one_line_core"].startswith("Agent evaluation")
    assert outputs["forecast"]["most_likely_case"] == "benchmark competition intensifies"


def test_run_staged_ai_pipeline_falls_back_when_ai_errors(monkeypatch):
    candidate = TopicCandidate(
        topic_id="topic-1",
        title="Edge NPU launch",
        url="https://example.com/npu",
        primary_domain="ai-x-electronics",
        matched_domains=["ai-x-electronics"],
        evidence_count=1,
        source_ids=["arm-news"],
        tags=["npu"],
        evidence_snippets=["Edge NPU release"],
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.summarize_with_deepseek",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "fallback"
    assert outputs["stage_status"]["summary"] == "fallback"
    assert outputs["stage_status"]["forecast"] == "fallback"
