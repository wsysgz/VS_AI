from auto_report.outputs.renderers import (
    render_markdown_report,
    render_telegram_notification,
    render_text_notification,
)


def _sample_payload() -> dict[str, object]:
    return {
        "one_line_core": "Agent 工具链继续向专业化和评估化收敛。",
        "executive_summary": ["评估框架继续增加。", "部署链路开始收敛。"],
        "key_points": [
            {"title": "评估框架增加", "why_it_matters": "可靠性门槛提高"},
            {"title": "模型发布提速", "why_it_matters": "生态竞争升温"},
        ],
        "key_insights": ["评估与交付开始绑定出现。"],
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
        "meta": {"total_items": 12, "total_topics": 5},
        "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
    }


def test_render_text_notification_uses_executive_brief_short_shape():
    text = render_text_notification(
        title="AI情报早报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "今日判断：" in text
    assert "三条主线：" in text
    assert "1. 评估框架增加" in text
    assert "提醒：" in text
    assert "观察：" in text


def test_render_telegram_notification_uses_full_brief_shape():
    text = render_telegram_notification(
        title="AI情报完整简报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "执行摘要" in text
    assert "关键主线" in text
    assert "重点主题" in text
    assert "局限与提醒" in text


def test_render_markdown_report_uses_formal_brief_sections():
    report = render_markdown_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "# 自动情报快报" in report
    assert "## 一句话判断" in report
    assert "## 重点主线" in report
    assert "## 重点主题分析" in report
    assert "## 行动建议" in report
