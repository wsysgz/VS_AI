from __future__ import annotations

import json

from auto_report.pipeline.briefing import compose_executive_brief


def render_markdown_report(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    key_insights = "\n".join(f"- {item}" for item in brief["key_insights"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"]
    ) or "- 暂无"
    limitations = "\n".join(f"- {item}" for item in brief["limitations"]) or "- 暂无"
    actions = "\n".join(f"- {item}" for item in brief["actions"]) or "- 暂无"

    lines = [
        f"# {title}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 一句话判断",
        str(brief["judgment"]),
        "",
        "## 执行摘要",
        executive_summary,
        "",
        "## 关键洞察",
        key_insights,
        "",
        "## 重点主线",
        mainlines,
        "",
        "## 重点主题分析",
    ]

    for topic in brief["topic_briefs"]:
        lines.extend(
            [
                f"### {topic['title']}",
                f"- 主领域：{topic['primary_domain']}",
                f"- 主要矛盾：{topic['primary_contradiction']}",
                f"- 核心洞察：{topic['core_insight']}",
                f"- 置信度：{topic['confidence']}",
                f"- 链接：{topic['url']}",
                "",
            ]
        )

    lines.extend(
        [
            "## 短期推演",
            f"- 观察：{brief['watchlist']}",
            f"- 结论：{brief['forecast_conclusion'] or '暂无'}",
            "",
            "## 局限性",
            limitations,
            "",
            "## 行动建议",
            actions,
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_json_report(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def render_text_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    detail_url: str,
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    lines = [
        title,
        f"生成时间：{generated_at}",
        "今日判断：",
        str(brief["judgment"]),
        "三条主线：",
    ]

    for index, item in enumerate(brief["mainlines"], start=1):
        lines.append(f"{index}. {item['title']}：{item['why_it_matters']}")

    if brief["risk_note"]:
        lines.extend(["提醒：", brief["risk_note"]])

    lines.extend(["观察：", brief["watchlist"], "详情链接：", detail_url])
    return "\n".join(lines)


def render_telegram_notification(
    title: str,
    generated_at: str,
    payload: dict[str, object],
    detail_url: str,
) -> str:
    brief = compose_executive_brief(title, generated_at, payload)
    executive_summary = "\n".join(f"- {item}" for item in brief["executive_summary"]) or "- 暂无"
    mainlines = "\n".join(
        f"- {item['title']}：{item['why_it_matters']}"
        for item in brief["mainlines"]
    ) or "- 暂无"
    topics = "\n".join(
        f"- {item['title']}：{item['core_insight']}"
        for item in brief["topic_briefs"]
    ) or "- 暂无"

    lines = [
        title,
        f"生成时间：{generated_at}",
        "",
        "今日判断：",
        str(brief["judgment"]),
        "",
        "执行摘要",
        executive_summary,
        "",
        "关键主线",
        mainlines,
        "",
        "重点主题",
        topics,
        "",
        "短期观察",
        f"- {brief['watchlist']}",
    ]

    if brief["risk_note"]:
        lines.extend(["", "局限与提醒", f"- {brief['risk_note']}"])

    lines.extend(["", "详情链接：", detail_url])
    return "\n".join(lines)
