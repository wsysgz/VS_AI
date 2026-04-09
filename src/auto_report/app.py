from __future__ import annotations

from datetime import datetime
from pathlib import Path

from auto_report.integrations.deepseek import summarize_with_deepseek
from auto_report.integrations.pushplus import send_pushplus
from auto_report.outputs.archive import write_text
from auto_report.outputs.renderers import render_json_report, render_markdown_report
from auto_report.pipeline.analysis import ReportPackage, build_report_package
from auto_report.pipeline.run_once import build_run_status
from auto_report.settings import Settings, load_settings
from auto_report.sources.collector import collect_all_items


def _format_signal_section(signals: list[dict[str, object]]) -> str:
    if not signals:
        return "## 主题信号\n- 本轮没有形成可展示的主题信号。\n"

    blocks: list[str] = ["## 主题信号"]
    for index, signal in enumerate(signals[:8], start=1):
        tags = "、".join(signal.get("tags", [])) or "无"
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {signal['title']}",
                    f"- 主领域：{signal['primary_domain']}",
                    f"- 证据数：{signal['evidence_count']}",
                    f"- 评分：{signal['score']}",
                    f"- 标签：{tags}",
                    f"- 摘要：{signal['summary']}",
                    f"- 链接：{signal['url']}",
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def _compose_report_markdown(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    predictions = payload.get("predictions", [])
    prediction_lines = "\n".join(f"- {item}" for item in predictions) or "- 暂无趋势提示"
    signals = payload.get("signals", [])
    base = render_markdown_report(
        title=title,
        generated_at=generated_at,
        highlights=payload.get("highlights", []),
        risks=payload.get("risks", []),
    )
    return (
        base
        + "\n"
        + _format_signal_section(signals)
        + "\n## 趋势提示\n"
        + prediction_lines
        + "\n"
    )


def _maybe_enrich_with_ai(package: ReportPackage, settings: Settings) -> None:
    if not settings.env["DEEPSEEK_API_KEY"] or not package.signals:
        package.summary_payload["risks"].append("未配置 DeepSeek API，当前使用规则摘要模式。")
        return

    prompt_lines = [
        "请基于以下主题信号，输出一段中文简报，包含：",
        "1. 当前最值得关注的变化",
        "2. 对 AI / 大模型 / Agent 的判断",
        "3. 对 AI x 电子信息的判断",
        "4. 一条谨慎的短期趋势提示",
        "",
    ]
    for index, signal in enumerate(package.signals[:6], start=1):
        prompt_lines.append(
            f"{index}. 标题：{signal.title}；领域：{signal.primary_domain}；标签：{'、'.join(signal.tags)}；摘要：{signal.summary}"
        )

    try:
        ai_summary = summarize_with_deepseek("\n".join(prompt_lines))
        package.summary_payload["highlights"].insert(0, f"AI分析补充：{ai_summary}")
        package.summary_payload["predictions"].insert(0, "已启用 DeepSeek 分析增强，请结合原始链接交叉判断。")
    except Exception as exc:
        package.summary_payload["risks"].append(f"DeepSeek 分析失败，已回退到规则摘要：{exc}")


def _write_domain_briefs(root_dir: Path, generated_at: str, package: ReportPackage, settings: Settings) -> list[str]:
    reports_dir = root_dir / "data" / "reports"
    generated: list[str] = []
    for domain_key, domain in settings.domains.items():
        file_name = f"latest-{domain_key}.md"
        path = reports_dir / file_name
        domain_payload = package.domain_payloads.get(domain_key, {})
        markdown = _compose_report_markdown(
            title=domain.get("title", domain_key),
            generated_at=generated_at,
            payload=domain_payload,
        )
        write_text(path, markdown)
        generated.append(str(path))
    return generated


def render_reports(root_dir: Path) -> list[str]:
    settings = load_settings(root_dir)
    generated_at = datetime.now().astimezone().isoformat()
    reports_dir = root_dir / "data" / "reports"
    state_dir = root_dir / "data" / "state"
    archive_dir = root_dir / "data" / "archives" / generated_at[:10]

    items, diagnostics = collect_all_items(settings)
    package = build_report_package(settings, items, diagnostics)
    package.summary_payload["meta"]["generated_at"] = generated_at
    _maybe_enrich_with_ai(package, settings)

    summary_markdown = _compose_report_markdown(
        title="自动情报快报",
        generated_at=generated_at,
        payload=package.summary_payload,
    )
    summary_json = render_json_report(package.summary_payload)

    summary_md_path = reports_dir / "latest-summary.md"
    summary_json_path = reports_dir / "latest-summary.json"
    archive_md_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.md"
    archive_json_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.json"
    dedup_state_path = state_dir / "dedup-index.json"

    write_text(summary_md_path, summary_markdown)
    write_text(summary_json_path, summary_json)
    write_text(archive_md_path, summary_markdown)
    write_text(archive_json_path, summary_json)
    write_text(dedup_state_path, render_json_report(package.dedup_state))

    generated_files = [
        str(summary_md_path),
        str(summary_json_path),
        str(archive_md_path),
        str(archive_json_path),
        str(dedup_state_path),
    ]
    generated_files.extend(_write_domain_briefs(root_dir, generated_at, package, settings))
    return generated_files


def run_once(root_dir: Path) -> list[str]:
    settings = load_settings(root_dir)
    generated_files = render_reports(root_dir)
    pushed = False

    if (
        settings.env["AUTO_PUSH_ENABLED"].lower() == "true"
        and settings.env["PUSHPLUS_TOKEN"]
    ):
        send_pushplus(
            settings.env["PUSHPLUS_TOKEN"],
            "自动情报快报",
            (root_dir / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8"),
        )
        pushed = True

    status = build_run_status(generated_files=generated_files, pushed=pushed)
    status_path = root_dir / "data" / "state" / "run-status.json"
    write_text(status_path, render_json_report(status))
    generated_files.append(str(status_path))
    return generated_files
