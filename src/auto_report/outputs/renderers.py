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
