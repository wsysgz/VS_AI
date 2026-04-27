from auto_report.outputs.renderers import (
    render_feishu_card_notification,
    render_feishu_notification,
    render_html_report,
    render_markdown_report,
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
        "meta": {
            "total_items": 12,
            "total_topics": 5,
            "publication_mode": "auto",
            "review": {"reviewer": "", "review_note": ""},
        },
        "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
    }


def test_render_text_notification_uses_executive_brief_short_shape():
    text = render_text_notification(
        title="AI情报早报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
        public_site_url="https://wsysgz.github.io/VS_AI/",
        raw_report_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert "今日判断：" in text
    assert "三条主线：" in text
    assert "国内外对比：" in text
    assert "frontier-ai：国内 Qwen edge agent release；海外 OpenAI agent runtime release。" in text
    assert "embedded：国内 RISC-V edge update；海外 NXP edge AI update。" in text
    assert "fpga：国内 FPGA update CN；海外 AMD Vitis update。" not in text
    assert "1. 评估框架增加" in text
    assert "提醒：" in text
    assert "观察：" in text
    assert "公开阅读：" in text
    assert "GitHub 原文：" in text


def test_render_feishu_notification_uses_mid_brief_shape():
    payload = _sample_payload()
    payload["meta"]["publication_mode"] = "reviewed"
    payload["meta"]["review"] = {"reviewer": "Alice", "review_note": "checked key sources"}
    text = render_feishu_notification(
        title="AI情报飞书简报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=payload,
        public_site_url="https://wsysgz.github.io/VS_AI/",
        raw_report_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert text.startswith("AI情报飞书简报 |")
    assert "执行摘要" in text
    assert "关键主线" in text
    assert "国内外对比" in text
    assert "frontier-ai：国内 Qwen edge agent release；海外 OpenAI agent runtime release。" in text
    assert "embedded：国内 RISC-V edge update；海外 NXP edge AI update。" in text
    assert "fpga：国内 FPGA update CN；海外 AMD Vitis update。" not in text
    assert "行动建议" in text
    assert "复核信息" in text
    assert "checked key sources" in text
    assert "重点主题" not in text
    assert "公开阅读：" in text
    assert "GitHub 原文：" in text


def test_render_feishu_card_notification_uses_static_card_shape():
    payload = _sample_payload()
    payload["meta"]["publication_mode"] = "reviewed"
    payload["meta"]["review"] = {"reviewer": "Alice", "review_note": "checked key sources"}
    card = render_feishu_card_notification(
        title="AI情报飞书简报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=payload,
        public_site_url="https://wsysgz.github.io/VS_AI/",
        raw_report_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    assert card["header"]["title"]["content"].startswith("AI情报飞书简报")
    assert card["header"]["template"] == "blue"
    assert any(
        element.get("text", {}).get("content", "").startswith("**国内外对比**")
        for element in card["elements"]
        if isinstance(element.get("text"), dict)
    )
    card_text = "\n".join(
        str(element.get("text", {}).get("content", ""))
        for element in card["elements"]
        if isinstance(element.get("text"), dict)
    )
    assert "frontier-ai：国内 Qwen edge agent release；海外 OpenAI agent runtime release。" in card_text
    assert "embedded：国内 RISC-V edge update；海外 NXP edge AI update。" in card_text
    assert "fpga：国内 FPGA update CN；海外 AMD Vitis update。" not in card_text
    assert any(element.get("tag") == "action" for element in card["elements"])
    action = next(element for element in card["elements"] if element.get("tag") == "action")
    assert action["actions"][0]["url"] == "https://wsysgz.github.io/VS_AI/"
    assert action["actions"][1]["url"].startswith("https://github.com/wsysgz/VS_AI/")


def test_render_feishu_card_notification_uses_real_newlines_in_markdown():
    payload = _sample_payload()
    payload["meta"]["publication_mode"] = "reviewed"
    card = render_feishu_card_notification(
        title="AI情报飞书简报 | 2026-04-10 | 北京时间 07:00",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=payload,
        public_site_url="https://wsysgz.github.io/VS_AI/",
        raw_report_url="https://github.com/wsysgz/VS_AI/blob/main/data/reports/latest-summary.md",
    )

    markdown_blocks: list[str] = []
    for element in card["elements"]:
        text = element.get("text")
        if isinstance(text, dict):
            markdown_blocks.append(str(text.get("content", "")))
        for field in element.get("fields", []):
            if isinstance(field, dict):
                field_text = field.get("text")
                if isinstance(field_text, dict):
                    markdown_blocks.append(str(field_text.get("content", "")))

    assert any("\n" in block for block in markdown_blocks)
    assert all("\\n" not in block for block in markdown_blocks)


def test_render_markdown_report_uses_formal_brief_sections():
    report = render_markdown_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "# 自动情报快报" in report
    assert "## 一句话判断" in report
    assert "## 重点主线" in report
    assert "## 国内外对比" in report
    assert "### 国内高亮信号" in report
    assert "Qwen edge agent release" in report
    assert "### 海外高亮信号" in report
    assert "OpenAI agent runtime release" in report
    assert "### 同轨对照" in report
    assert "fpga：国内 FPGA update CN；海外 AMD Vitis update。" in report
    assert "### 覆盖缺口" in report
    assert "personal-hpc：仅看到海外信号，需补齐国内来源。" in report
    assert "### 观察点" in report
    assert "## 跨日主线记忆" in report
    assert "## 重点主题分析" in report
    assert "## 行动建议" in report
    assert "生命周期：verified" in report
    assert "风险等级：low" in report
    assert "OpenAI launches agent debugger" in report


def test_render_html_report_produces_valid_document():
    html = render_html_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html
    assert "自动情报快报" in html
    assert "2026-04-10" in html


def test_render_html_report_contains_key_sections():
    html = render_html_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "执行摘要" in html
    assert "关键洞察" in html
    assert "重点主线" in html
    assert "跨日主线记忆" in html
    assert "Signal A" in html
    assert "评估框架增加" in html
    assert "继续看真实落地反馈" in html
    assert "OpenAI launches agent debugger" in html


def test_render_html_report_escapes_special_characters():
    payload = _sample_payload()
    payload["one_line_core"] = 'Test with <script>alert("xss")</script> & "quotes"'
    html = render_html_report(title="Test", generated_at="2026-04-10", payload=payload)

    assert "<script>" not in html or "&lt;script&gt;" in html
    assert "&amp;" in html or "&" not in html.split("<body")[1].split("</body>")[0]


def test_render_html_report_includes_stage_badges_and_stats():
    html = render_html_report(
        title="自动情报快报",
        generated_at="2026-04-10T07:00:00+08:00",
        payload=_sample_payload(),
    )

    assert "12 条原始信息" in html
    assert "5 个主题" in html
    assert "analysis: ok" in html
