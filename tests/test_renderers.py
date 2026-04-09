from auto_report.outputs.renderers import render_markdown_report, render_text_notification


def test_render_markdown_report_contains_title_and_sections():
    report = render_markdown_report(
        title="每日总报",
        generated_at="2026-04-09T08:00:00+08:00",
        highlights=["Highlight A", "Highlight B"],
        risks=["Risk A"],
    )

    assert "# 每日总报" in report
    assert "## 核心看点" in report
    assert "## 风险与备注" in report


def test_render_text_notification_includes_short_items_and_detail_link():
    text = render_text_notification(
        title="自动情报快报",
        generated_at="2026-04-09T08:00:00+08:00",
        payload={
            "signals": [
                {"title": "DeepSeek API Docs"},
                {"title": "Holotron-12B"},
                {"title": "Safetensors joins foundation"},
            ],
            "predictions": ["Agent 工具链继续升温"],
        },
        detail_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "自动情报快报" in text
    assert "核心看点：" in text
    assert "1. DeepSeek API Docs" in text
    assert "趋势提示：" in text
    assert "详情链接：" in text
    assert "https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md" in text
