from auto_report.outputs.renderers import render_markdown_report, render_text_notification


def test_render_markdown_report_contains_title_and_sections():
    report = render_markdown_report(
        title="每日总报",
        generated_at="2026-04-09T08:00:00+08:00",
        payload={
            "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
            "executive_summary": ["Highlight A", "Highlight B"],
            "key_insights": ["Insight A"],
            "analyses": [
                {
                    "title": "Signal A",
                    "primary_domain": "ai-llm-agent",
                    "primary_contradiction": "speed vs reliability",
                    "core_insight": "Insight",
                    "confidence": "medium",
                    "url": "https://example.com/a",
                }
            ],
            "forecast": {
                "most_likely_case": "Short-term consolidation",
                "forecast_conclusion": "Watch evaluation quality",
            },
            "limitations": ["Risk A"],
        },
    )

    assert "# 每日总报" in report
    assert "## 一句话核心" in report
    assert "## 执行摘要" in report
    assert "## 短期预测" in report


def test_render_text_notification_uses_morning_brief_shape():
    text = render_text_notification(
        title="AI情报早报 | 04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload={
            "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
            "key_points": [
                {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
                {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
            ],
            "forecast": {"most_likely_case": "短期继续围绕评估与部署演进"},
            "limitations": ["部分信号仍需复核"],
        },
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "AI情报早报 | 04-10 | 北京时间 07:00" in text
    assert "今日一句话：" in text
    assert "【主线】评估框架增加" in text
    assert "【提醒】部分信号仍需复核" in text
    assert "详情链接：" in text
    assert "https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md" in text
