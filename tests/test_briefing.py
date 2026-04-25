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
                    "lifecycle_state": "verified",
                    "risk_level": "low",
                    "enrichment": {"summary": "2 source(s) | official / repo"},
                    "support_evidence": [
                        {
                            "source_type": "official",
                            "title": "OpenAI launches agent debugger",
                            "url": "https://openai.com/news/agent-debugger",
                        }
                    ],
                }
            ],
            "mainline_memory": [
                {
                    "title": "Signal A",
                    "lifecycle_state": "verified",
                    "risk_level": "low",
                    "days_seen": 3,
                    "first_seen": "2026-04-08",
                    "last_seen": "2026-04-10",
                    "enrichment_summary": "2 source(s) | official / repo",
                }
            ],
            "forecast": {
                "most_likely_case": "短期继续围绕评估与部署演进",
                "forecast_conclusion": "继续看真实落地反馈。",
            },
            "limitations": ["部分信号仍需复核"],
            "actions": ["继续跟踪评估框架"],
            "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
            "comparison_brief": {
                "cn_highlights": [
                    {
                        "title": "Qwen edge agent release",
                        "tech_track": "frontier-ai",
                        "source_ids": ["qwen-blog"],
                    }
                ],
                "intl_highlights": [
                    {
                        "title": "OpenAI agent runtime release",
                        "tech_track": "frontier-ai",
                        "source_ids": ["openai-news"],
                    }
                ],
                "head_to_head": [
                    {
                        "tech_track": "frontier-ai",
                        "cn_title": "Qwen edge agent release",
                        "intl_title": "OpenAI agent runtime release",
                        "readout": "frontier-ai：国内 Qwen edge agent release；海外 OpenAI agent runtime release。",
                    },
                    {
                        "tech_track": "embedded",
                        "cn_title": "RISC-V edge update",
                        "intl_title": "NXP edge AI update",
                        "readout": "embedded：国内 RISC-V edge update；海外 NXP edge AI update。",
                    },
                    {
                        "tech_track": "fpga",
                        "cn_title": "FPGA update CN",
                        "intl_title": "AMD Vitis update",
                        "readout": "fpga：国内 FPGA update CN；海外 AMD Vitis update。",
                    },
                ],
                "gaps": ["personal-hpc：仅看到海外信号，需补齐国内来源。"],
                "watchpoints": ["继续跟踪 frontier-ai 的同轨交付反馈。"],
            },
        },
    )

    assert brief["judgment"] == "Agent 工具链继续向专业化和评估化收敛。"
    assert brief["mainlines"][0]["title"] == "评估框架增加"
    assert brief["topic_briefs"][0]["title"] == "Signal A"
    assert brief["topic_briefs"][0]["lifecycle_state"] == "verified"
    assert brief["topic_briefs"][0]["risk_level"] == "low"
    assert brief["topic_briefs"][0]["support_evidence"][0]["source_type"] == "official"
    assert brief["mainline_memory"][0]["days_seen"] == 3
    assert brief["watchlist"] == "短期继续围绕评估与部署演进"
    assert brief["risk_note"] == "部分信号仍需复核"
    assert brief["action_note"] == "继续跟踪评估框架"
    assert brief["comparison_brief"]["gaps"][0] == "personal-hpc：仅看到海外信号，需补齐国内来源。"
    assert brief["comparison_head_to_head"] == [
        "frontier-ai：国内 Qwen edge agent release；海外 OpenAI agent runtime release。",
        "embedded：国内 RISC-V edge update；海外 NXP edge AI update。",
    ]


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
    assert brief["mainline_memory"] == []
    assert brief["topic_briefs"] == []
    assert brief["watchlist"] == "本轮先保持观察，等待更多高置信度信号。"
    assert brief["risk_note"] == ""
    assert brief["action_note"] == ""
    assert brief["comparison_brief"] == {
        "cn_highlights": [],
        "intl_highlights": [],
        "head_to_head": [],
        "gaps": [],
        "watchpoints": [],
    }
    assert brief["comparison_head_to_head"] == []
