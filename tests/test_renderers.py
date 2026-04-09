from auto_report.outputs.renderers import render_markdown_report


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
