from __future__ import annotations

import json


def render_markdown_report(
    title: str,
    generated_at: str,
    highlights: list[str],
    risks: list[str],
) -> str:
    highlight_lines = "\n".join(f"- {item}" for item in highlights) or "- None"
    risk_lines = "\n".join(f"- {item}" for item in risks) or "- None"
    return (
        f"# {title}\n\n"
        f"生成时间：{generated_at}\n\n"
        "## 核心看点\n"
        f"{highlight_lines}\n\n"
        "## 风险与备注\n"
        f"{risk_lines}\n"
    )


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
        "核心看点：",
    ]

    signals = payload.get("signals", [])
    if isinstance(signals, list) and signals:
        for index, signal in enumerate(signals[:3], start=1):
            signal_title = str(signal.get("title", "未命名主题")).strip()
            lines.append(f"{index}. {signal_title[:72]}")
    else:
        highlights = payload.get("highlights", [])
        for index, highlight in enumerate(highlights[:3], start=1):
            lines.append(f"{index}. {str(highlight).strip()[:72]}")

    lines.append("趋势提示：")
    predictions = payload.get("predictions", [])
    if isinstance(predictions, list) and predictions:
        lines.append(f"- {str(predictions[0]).strip()[:88]}")
    else:
        lines.append("- 暂无趋势提示")

    lines.append("详情链接：")
    lines.append(detail_url)
    return "\n".join(lines)
