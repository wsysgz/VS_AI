from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from auto_report.integrations.pushplus import send_pushplus
from auto_report.integrations.telegram import send_telegram_messages
from auto_report.outputs.archive import write_text
from auto_report.outputs.renderers import (
    render_json_report,
    render_markdown_report,
    render_telegram_notification,
    render_text_notification,
)
from auto_report.pipeline.analysis import build_report_package
from auto_report.pipeline.run_once import build_run_status
from auto_report.settings import load_settings
from auto_report.sources.collector import collect_all_items


def _compose_report_markdown(
    title: str,
    generated_at: str,
    payload: dict[str, object],
) -> str:
    return render_markdown_report(
        title=title,
        generated_at=generated_at,
        payload=payload,
    )

def _write_domain_briefs(root_dir: Path, generated_at: str, package, settings) -> list[str]:
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


def _load_summary_payload(root_dir: Path) -> dict[str, object]:
    summary_json_path = root_dir / "data" / "reports" / "latest-summary.json"
    return json.loads(summary_json_path.read_text(encoding="utf-8"))


def _build_detail_url(settings) -> str:
    base_url = settings.env["REPORT_REPO_URL"].rstrip("/")
    return f"{base_url}/blob/main/data/reports/latest-summary.md"


def _build_text_notification(root_dir: Path, settings) -> str:
    payload = _load_summary_payload(root_dir)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    return render_text_notification(
        title=f"AI情报早报 | {local_date} | 北京时间 07:00",
        generated_at=generated_at,
        payload=payload,
        detail_url=_build_detail_url(settings),
    )


def _build_telegram_notification(root_dir: Path, settings) -> str:
    payload = _load_summary_payload(root_dir)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    detail_url = _build_detail_url(settings)
    return render_telegram_notification(
        title=f"AI情报完整简报 | {local_date} | 北京时间 07:00",
        generated_at=generated_at,
        payload=payload,
        detail_url=detail_url,
    )


def render_reports(root_dir: Path) -> list[str]:
    settings = load_settings(root_dir)
    generated_at = datetime.now().astimezone().isoformat()
    reports_dir = root_dir / "data" / "reports"
    state_dir = root_dir / "data" / "state"
    archive_dir = root_dir / "data" / "archives" / generated_at[:10]

    items, diagnostics = collect_all_items(settings)
    package = build_report_package(settings, items, diagnostics)
    package.summary_payload["meta"]["generated_at"] = generated_at

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
    summary_payload = _load_summary_payload(root_dir)
    pushed = False
    push_channel = ""
    push_response: dict[str, object] = {}

    if settings.env["AUTO_PUSH_ENABLED"].lower() == "true":
        text_notification = _build_text_notification(root_dir, settings)
        notification_results: dict[str, object] = {}

        if settings.env["PUSHPLUS_TOKEN"]:
            push_channel = settings.env["PUSHPLUS_CHANNEL"]
            push_response = send_pushplus(
                settings.env["PUSHPLUS_TOKEN"],
                "自动情报快报",
                text_notification if push_channel == "clawbot" else (root_dir / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8"),
                channel=push_channel,
                template="txt" if push_channel == "clawbot" else "markdown",
            )
            notification_results["pushplus"] = push_response

        if settings.env["TELEGRAM_BOT_TOKEN"] and settings.env["TELEGRAM_CHAT_ID"]:
            notification_results["telegram"] = send_telegram_messages(
                settings.env["TELEGRAM_BOT_TOKEN"],
                settings.env["TELEGRAM_CHAT_ID"],
                _build_telegram_notification(root_dir, settings),
            )

        if notification_results:
            push_response = notification_results
            pushed = True

    status = build_run_status(
        generated_files=generated_files,
        pushed=pushed,
        push_channel=push_channel,
        push_response=push_response,
        stage_status=summary_payload.get("stage_status", {}),
        source_stats={
            "collected_items": int(summary_payload.get("meta", {}).get("total_items", 0)),
            "filtered_topics": int(summary_payload.get("meta", {}).get("total_topics", 0)),
        },
    )
    status_path = root_dir / "data" / "state" / "run-status.json"
    write_text(status_path, render_json_report(status))
    generated_files.append(str(status_path))
    return generated_files
