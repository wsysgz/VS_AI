from auto_report.models.records import TopicCandidate
from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline


def test_run_staged_ai_pipeline_returns_structured_outputs(monkeypatch):
    monkeypatch.setenv("AI_MODEL", "deepseek-v4-flash")

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
            '{"one_line_core":"Agent 评测正成为核心战场","executive_summary":["A","B"],"key_points":[{"title":"信号","why_it_matters":"重要"}],"key_insights":["Insight"],"limitations":["需要验证"],"actions":["跟踪基准"]}',
            '{"most_likely_case":"基准竞争继续升温","best_case":"更好的可靠性","worst_case":"基准表演化","key_variables":["真实部署"],"forecast_conclusion":"关注评测质量","confidence":"medium"}',
            ]
        )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.call_llm",
        lambda prompt, stage=None: next(responses),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "ok"
    assert outputs["summary"]["one_line_core"].startswith("Agent 评测")
    assert outputs["forecast"]["most_likely_case"] == "基准竞争继续升温"
    assert outputs["ai_metrics"]["provider"] == "deepseek"
    assert outputs["ai_metrics"]["model"] == "deepseek-v4-flash"
    assert outputs["ai_metrics"]["token_usage"]["total"] == 0
    assert outputs["ai_metrics"]["fallback_stages"] == []


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
        "auto_report.pipeline.ai_pipeline.call_llm",
        lambda prompt, stage=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    # Phase 1.1 并行化后：单个候选失败走 fallback 补充，整体分析状态仍为 ok
    assert outputs["stage_status"]["analysis"] == "ok"
    assert len(outputs["analyses"]) == 1
    # 但后续 summary/forecast 调用仍会失败(DeepSeek 被 mock 为抛异常)
    assert outputs["stage_status"]["summary"] == "fallback"
    assert outputs["stage_status"]["forecast"] == "fallback"
    assert outputs["ai_metrics"]["fallback_stages"] == ["summary", "forecast"]


def test_run_staged_ai_pipeline_limits_analysis_scope(monkeypatch):
    candidates = [
        TopicCandidate(
            topic_id=f"topic-{index}",
            title=f"Topic {index}",
            url=f"https://example.com/{index}",
            primary_domain="ai-llm-agent",
            matched_domains=["ai-llm-agent"],
            evidence_count=1,
            source_ids=["openai-news"],
            tags=["agent"],
            evidence_snippets=[f"Snippet {index}"],
        )
        for index in range(1, 3)
    ]

    call_counter = {"count": 0}
    responses = iter(
        [
            '{"facts":["Fact"],"contradictions":["A vs B"],"primary_contradiction":"A vs B","core_insight":"Insight","confidence":"medium"}',
            '{"one_line_core":"核心判断","executive_summary":["A"],"key_points":[{"title":"信号","why_it_matters":"重要"}],"key_insights":["Insight"],"limitations":["需要验证"],"actions":["跟踪"]}',
            '{"most_likely_case":"大概率继续","best_case":"最佳","worst_case":"最差","key_variables":["变量"],"forecast_conclusion":"结论","confidence":"medium"}',
        ]
    )

    def fake_summarize(prompt: str, stage: str | None = None) -> str:
        call_counter["count"] += 1
        return next(responses)

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.call_llm",
        fake_summarize,
    )

    outputs = run_staged_ai_pipeline(
        candidates=candidates,
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
        max_candidates=1,
    )

    assert call_counter["count"] == 3
    assert len(outputs["analyses"]) == 1
    assert outputs["analyses"][0]["title"] == "Topic 1"


def test_run_staged_ai_pipeline_falls_back_when_summary_shape_is_invalid(monkeypatch):
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
            '{"analysis":{"facts":["Release published"],"contradictions":["speed vs reliability"],"primary_contradiction":"speed vs reliability","core_insight":"evaluation is becoming central","confidence":"medium"}}',
            '{"analysis":{"situation_overview":"This is not a summary payload"}}',
        ]
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.call_llm",
        lambda prompt, stage=None: next(responses),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["analysis"] == "ok"
    assert outputs["analyses"][0]["core_insight"] == "evaluation is becoming central"
    assert outputs["stage_status"]["summary"] == "fallback"
    assert outputs["stage_status"]["forecast"] == "fallback"


def test_run_staged_ai_pipeline_falls_back_when_summary_and_forecast_are_english_only(monkeypatch):
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
            '{"one_line_core":"The latest AI agent evaluation wave is intensifying rapidly","executive_summary":["A","B"],"key_points":[{"title":"Signal","why_it_matters":"Matters"}],"key_insights":["Insight"],"limitations":["Need verification"],"actions":["Track benchmarks"]}',
            '{"best_case":"Improves","worst_case":"Lags","most_likely_case":"Continues","key_variables":["deployment"],"forecast_conclusion":"Watch evaluation quality","confidence":"medium"}',
        ]
    )

    monkeypatch.setattr(
        "auto_report.pipeline.ai_pipeline.call_llm",
        lambda prompt, stage=None: next(responses),
    )

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert outputs["stage_status"]["summary"] == "fallback"
    assert outputs["stage_status"]["forecast"] == "fallback"
    assert outputs["summary"]["one_line_core"].startswith("本轮采集到")
    assert outputs["forecast"]["forecast_conclusion"].startswith("本轮预测阶段已回退")


def test_run_staged_ai_pipeline_routes_each_stage_to_named_provider(monkeypatch):
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

    calls: list[str] = []

    def fake_call(prompt: str, stage: str | None = None) -> str:
        calls.append(stage or "")
        if stage == "analysis":
            return '{"facts":["Release published"],"contradictions":["speed vs reliability"],"primary_contradiction":"speed vs reliability","core_insight":"evaluation is becoming central","confidence":"medium"}'
        if stage == "summary":
            return '{"one_line_core":"Agent 评测正成为核心战场","executive_summary":["A","B"],"key_points":[{"title":"信号","why_it_matters":"重要"}],"key_insights":["Insight"],"limitations":["需要验证"],"actions":["跟踪基准"]}'
        if stage == "forecast":
            return '{"most_likely_case":"基准竞争继续升温","best_case":"更好的可靠性","worst_case":"基准表演化","key_variables":["真实部署"],"forecast_conclusion":"关注评测质量","confidence":"medium"}'
        raise AssertionError(f"unexpected stage: {stage}")

    monkeypatch.setattr("auto_report.pipeline.ai_pipeline.call_llm", fake_call)

    outputs = run_staged_ai_pipeline(
        candidates=[candidate],
        ai_readings={"analysis": "analysis-rules", "summary": "summary-rules", "forecast": "forecast-rules"},
        ai_enabled=True,
    )

    assert calls == ["analysis", "summary", "forecast"]
    assert outputs["stage_status"]["analysis"] == "ok"
    assert outputs["stage_status"]["summary"] == "ok"
    assert outputs["stage_status"]["forecast"] == "ok"
