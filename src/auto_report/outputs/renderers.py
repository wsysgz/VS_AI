from __future__ import annotations

import json


def render_markdown_report(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    executive_summary = "\n".join(f"- {item}" for item in payload.get("executive_summary", [])) or "- 暂无"
    key_insights = "\n".join(f"- {item}" for item in payload.get("key_insights", [])) or "- 暂无"
    limitations = "\n".join(f"- {item}" for item in payload.get("limitations", [])) or "- 暂无"
    forecast = payload.get("forecast", {})
    analyses = payload.get("analyses", [])

    lines = [
        f"# {title}",
        "",
        f"生成时间：{generated_at}",
        "",
        "## 一句话核心",
        str(payload.get("one_line_core", "暂无核心判断")),
        "",
        "## 执行摘要",
        executive_summary,
        "",
        "## 关键洞察",
        key_insights,
        "",
        "## 主题分析",
    ]

    for analysis in analyses[:6]:
        lines.extend(
            [
                f"### {analysis.get('title', '未命名主题')}",
                f"- 主领域：{analysis.get('primary_domain', 'unknown')}",
                f"- 主要矛盾：{analysis.get('primary_contradiction', '待补充')}",
                f"- 核心洞察：{analysis.get('core_insight', '待补充')}",
                f"- 置信度：{analysis.get('confidence', 'low')}",
                f"- 链接：{analysis.get('url', '')}",
                "",
            ]
        )

    lines.extend(
        [
            "## 短期预测",
            f"- 最可能：{forecast.get('most_likely_case', '暂无')}",
            f"- 结论：{forecast.get('forecast_conclusion', '暂无')}",
            "",
            "## 局限性",
            limitations,
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
    lines = [
        title,
        f"生成时间：{generated_at}",
        "今日一句话：",
        str(payload.get("one_line_core", "暂无核心判断")),
        "今日三点：",
    ]

    for point in payload.get("key_points", [])[:3]:
        lines.append(f"【主线】{point.get('title', '未命名要点')}")
        lines.append(f"【影响】{point.get('why_it_matters', '需要继续观察')}")

    limitations = payload.get("limitations", [])
    if limitations:
        lines.append(f"【提醒】{limitations[0]}")

    forecast = payload.get("forecast", {})
    lines.append(f"【观察】{forecast.get('most_likely_case', '暂无趋势提示')}")

    lines.append("详情链接：")
    lines.append(detail_url)
    return "\n".join(lines)
