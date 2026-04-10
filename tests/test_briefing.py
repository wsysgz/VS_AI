from auto_report.pipeline.briefing import compose_executive_brief


def test_compose_executive_brief_builds_mainlines_topics_and_notes():
    brief = compose_executive_brief(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "meta": {"total_items": 12, "total_topics": 5},
            "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
            "executive_summary": ["评估框架继续增加。", "部署链路开始收敛。"],
            "key_points": [
                {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
                {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
            ],
            "key_insights": ["评估和交付正绑定出现。"],
            "analyses": [
                {
                    "title": "Signal A",
                    "primary_domain": "ai-llm-agent",
                    "primary_contradiction": "速度 vs 可靠性",
                    "core_insight": "评估开始前置。",
                    "confidence": "medium",
                    "url": "https://example.com/a",
                }
            ],
            "forecast": {
                "most_likely_case": "短期继续围绕评估与部署演进",
                "forecast_conclusion": "继续看真实落地反馈。",
            },
            "limitations": ["部分信号仍需复核"],
            "actions": ["继续跟踪评估框架"],
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
        },
    )

    assert brief["judgment"] == "Agent 工具链继续向专业化和评估化收敛。"
    assert brief["mainlines"][0]["title"] == "评估框架增加"
    assert brief["topic_briefs"][0]["title"] == "Signal A"
    assert brief["watchlist"] == "短期继续围绕评估与部署演进"
    assert brief["risk_note"] == "部分信号仍需复核"
    assert brief["action_note"] == "继续跟踪评估框架"


def test_compose_executive_brief_degrades_gracefully_with_sparse_payload():
    brief = compose_executive_brief(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "one_line_core": "",
            "executive_summary": [],
            "key_points": [],
            "key_insights": [],
            "analyses": [],
            "forecast": {},
            "limitations": [],
            "actions": [],
            "meta": {"total_items": 0, "total_topics": 0},
            "stage_status": {"analysis": "fallback", "summary": "fallback", "forecast": "fallback"},
        },
    )

    assert brief["judgment"] == "暂无核心判断"
    assert brief["mainlines"] == []
    assert brief["topic_briefs"] == []
    assert brief["watchlist"] == "本轮先保持观察，等待更多高置信度信号。"
    assert brief["risk_note"] == ""
    assert brief["action_note"] == ""
