from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from auto_report.integrations.delivery_status import (
    build_channel_result,
    classify_channel_error,
    channel_response_succeeded,
    describe_channel_response,
    summarize_delivery_results,
)
from auto_report.integrations.feishu import send_feishu_messages
from auto_report.integrations.llm_client import is_llm_enabled
from auto_report.integrations.pushplus import send_pushplus
from auto_report.integrations.telegram import send_telegram_messages
from auto_report.outputs.archive import write_text
from auto_report.outputs.ops_dashboard import build_ops_dashboard
from auto_report.outputs.renderers import (
    render_feishu_notification,
    render_html_report,
    render_json_report,
    render_markdown_report,
    render_pushplus_notification,
    render_telegram_notification,
)
from auto_report.pipeline.analysis import build_report_package
from auto_report.pipeline.run_once import build_run_status, _to_relative_paths
from auto_report.settings import load_settings
from auto_report.sources.collector import collect_all_items


PUBLIC_SITE_URL = "https://wsysgz.github.io/VS_AI/"


# ════════════════════════════════════════
# 阶段计时器 (Phase 4 可观测性前置)
# ════════════════════════════════════════

class StageTimer:
    """简易阶段计时器"""

    def __init__(self, name: str):
        self.name = name
        self.start: float = 0
        self.elapsed: float = 0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_args):
        self.elapsed = round(time.perf_counter() - self.start, 2)


def _normalize_publication_mode(value: str) -> str:
    return "reviewed" if str(value).strip().lower() == "reviewed" else "auto"


def _resolve_publication_mode(settings, publication_mode: str = "") -> str:
    requested = publication_mode or settings.env.get("PUBLICATION_MODE", "auto")
    return _normalize_publication_mode(requested)


def _resolve_review_metadata(
    settings,
    publication_mode: str,
    reviewer: str = "",
    review_note: str = "",
) -> dict[str, str]:
    if _normalize_publication_mode(publication_mode) != "reviewed":
        return {"reviewer": "", "review_note": ""}
    return {
        "reviewer": str(reviewer or settings.env.get("REPORT_REVIEWER", "")).strip(),
        "review_note": str(review_note or settings.env.get("REPORT_REVIEW_NOTE", "")).strip(),
    }


def _summary_track_stem(publication_mode: str) -> str:
    return f"latest-summary-{_normalize_publication_mode(publication_mode)}"


def _archive_track_stem(generated_at: str, publication_mode: str) -> str:
    return f"{generated_at.replace(':', '-')}-summary-{_normalize_publication_mode(publication_mode)}"


def _report_title(publication_mode: str, backfill: bool = False) -> str:
    title = "自动情报快报（人工复核版）" if _normalize_publication_mode(publication_mode) == "reviewed" else "自动情报快报"
    if backfill:
        return f"{title}（补报）"
    return title


def _classify_source_diagnostic(message: str) -> str:
    normalized = str(message or "").lower()
    if "404" in normalized or "not found" in normalized:
        return "not_found"
    if "timed out" in normalized or "timeout" in normalized:
        return "timeout"
    if any(token in normalized for token in ("request failed", "connection", "network", "http error", "api request failed")):
        return "request_error"
    if "failed:" in normalized or " failed" in normalized or "error" in normalized:
        return "request_error"
    return "other"


def _summarize_source_health(diagnostics: list[str]) -> dict[str, object]:
    summary = {
        "total": 0,
        "not_found": 0,
        "timeout": 0,
        "request_error": 0,
        "other": 0,
        "samples": [],
    }
    for message in diagnostics:
        text = str(message).strip()
        if not text:
            continue
        category = _classify_source_diagnostic(text)
        summary["total"] = int(summary["total"]) + 1
        summary[category] = int(summary[category]) + 1
        if len(summary["samples"]) < 6:
            summary["samples"].append(text)
    return summary


def _notification_title(prefix: str, publication_mode: str, local_date: str, review: dict[str, str] | None = None) -> str:
    if _normalize_publication_mode(publication_mode) == "reviewed":
        reviewer = str((review or {}).get("reviewer", "")).strip()
        review_suffix = f" / {reviewer}" if reviewer else ""
        return f"{prefix}（人工复核版{review_suffix}） | {local_date} | 北京时间 07:00"
    return f"{prefix} | {local_date} | 北京时间 07:00"


def _save_intermediate(root_dir: Path, data: dict) -> str:
    """保存采集中间结果供 analyze-only 使用"""
    state_dir = root_dir / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "intermediate.json"
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2))
    return str(path)


def _load_intermediate(root_dir: Path) -> dict:
    """加载中间结果"""
    path = root_dir / "data" / "state" / "intermediate.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _save_analysis_result(root_dir: Path, result: dict, meta: dict | None = None) -> str:
    """保存AI分析结果"""
    state_dir = root_dir / "data" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    payload = {"result": result}
    if meta:
        payload["meta"] = meta
    path = state_dir / "analysis-result.json"
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))
    return str(path)


def _load_analysis_result(root_dir: Path) -> dict:
    """加载分析结果"""
    path = root_dir / "data" / "state" / "analysis-result.json"
    return json.loads(path.read_text(encoding="utf-8"))


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


def _load_summary_payload(root_dir: Path, publication_mode: str = "auto") -> dict[str, object]:
    reports_dir = root_dir / "data" / "reports"
    candidates = [
        reports_dir / f"{_summary_track_stem(publication_mode)}.json",
        reports_dir / "latest-summary.json",
    ]
    for path in candidates:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Summary payload not found in {reports_dir}")


def _build_raw_report_url(settings, publication_mode: str) -> str:
    base_url = settings.env.get("REPORT_REPO_URL", "https://github.com/wsysgz/VS_AI").rstrip("/")
    return f"{base_url}/blob/main/data/reports/{_summary_track_stem(publication_mode)}.md"


def _build_text_notification(root_dir: Path, settings, publication_mode: str) -> str:
    payload = _load_summary_payload(root_dir, publication_mode=publication_mode)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    review = payload.get("meta", {}).get("review", {})
    if not isinstance(review, dict):
        review = {}
    return render_pushplus_notification(
        title=_notification_title("AI情报早报", publication_mode, local_date, review=review),
        generated_at=generated_at,
        payload=payload,
        public_site_url=PUBLIC_SITE_URL,
        raw_report_url=_build_raw_report_url(settings, publication_mode),
    )


def _build_telegram_notification(root_dir: Path, settings, publication_mode: str) -> str:
    payload = _load_summary_payload(root_dir, publication_mode=publication_mode)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    review = payload.get("meta", {}).get("review", {})
    if not isinstance(review, dict):
        review = {}
    return render_telegram_notification(
        title=_notification_title("AI情报完整简报", publication_mode, local_date, review=review),
        generated_at=generated_at,
        payload=payload,
        public_site_url=PUBLIC_SITE_URL,
        raw_report_url=_build_raw_report_url(settings, publication_mode),
    )


def _build_feishu_notification(root_dir: Path, settings, publication_mode: str) -> str:
    payload = _load_summary_payload(root_dir, publication_mode=publication_mode)
    generated_at = str(payload.get("meta", {}).get("generated_at", datetime.now().astimezone().isoformat()))
    local_date = generated_at[:10]
    review = payload.get("meta", {}).get("review", {})
    if not isinstance(review, dict):
        review = {}
    return render_feishu_notification(
        title=_notification_title("AI情报飞书简报", publication_mode, local_date, review=review),
        generated_at=generated_at,
        payload=payload,
        public_site_url=PUBLIC_SITE_URL,
        raw_report_url=_build_raw_report_url(settings, publication_mode),
    )


def _build_delivery_probe_messages() -> dict[str, dict[str, str]]:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "pushplus": {
            "title": "VS_AI delivery diagnostic",
            "content": f"VS_AI delivery diagnostic\n{timestamp}\nPushPlus/WeChat channel check.",
        },
        "telegram": {
            "text": f"VS_AI delivery diagnostic\n{timestamp}\nTelegram channel check.",
        },
        "feishu": {
            "text": f"VS_AI delivery diagnostic\n{timestamp}\nFeishu channel check.",
        },
    }


def _empty_delivery_results() -> dict[str, object]:
    return {
        "channels": {},
        "successful_channels": [],
        "failed_channels": [],
        "skipped_channels": [],
    }


def _scheduler_context(settings) -> dict[str, object]:
    return {
        "trigger_kind": settings.env.get("SCHEDULER_TRIGGER_KIND", "manual") or "manual",
        "compensation_run": settings.env.get("SCHEDULER_COMPENSATION_RUN", "false").lower() == "true",
    }


def _collect_delivery_results(
    root_dir: Path,
    settings,
    send: bool,
    mode: str = "full-report",
    publication_mode: str = "auto",
) -> tuple[dict[str, object], dict[str, object]]:
    responses: dict[str, object] = {}
    results: dict[str, dict[str, object]] = {}
    request_timeout = int(settings.env.get("DELIVERY_REQUEST_TIMEOUT", "20"))
    probe_messages = _build_delivery_probe_messages()

    pushplus_title = _report_title(publication_mode)
    pushplus_content = ""
    telegram_content = ""
    feishu_content = ""
    if send:
        if mode == "canary":
            pushplus_title = probe_messages["pushplus"]["title"]
            pushplus_content = probe_messages["pushplus"]["content"]
            telegram_content = probe_messages["telegram"]["text"]
            feishu_content = probe_messages["feishu"]["text"]
        else:
            pushplus_content = _build_text_notification(root_dir, settings, publication_mode)
            telegram_content = _build_telegram_notification(root_dir, settings, publication_mode)
            feishu_content = _build_feishu_notification(root_dir, settings, publication_mode)

    delivery_plan = [
        (
            "pushplus",
            bool(settings.env["PUSHPLUS_TOKEN"]),
            lambda: send_pushplus(
                settings.env["PUSHPLUS_TOKEN"],
                pushplus_title,
                pushplus_content,
                channel=settings.env["PUSHPLUS_CHANNEL"],
                template="txt",
                secret_key=settings.env.get("PUSHPLUS_SECRETKEY", ""),
                base_url=settings.env["PUSHPLUS_BASE_URL"],
                timeout=request_timeout,
            ),
        ),
        (
            "telegram",
            bool(settings.env["TELEGRAM_BOT_TOKEN"] and settings.env["TELEGRAM_CHAT_ID"]),
            lambda: send_telegram_messages(
                settings.env["TELEGRAM_BOT_TOKEN"],
                settings.env["TELEGRAM_CHAT_ID"],
                telegram_content,
                api_base_url=settings.env["TELEGRAM_API_BASE_URL"],
                timeout=request_timeout,
            ),
        ),
        (
            "feishu",
            bool(settings.env["FEISHU_APP_ID"] and settings.env["FEISHU_APP_SECRET"] and settings.env["FEISHU_CHAT_ID"]),
            lambda: send_feishu_messages(
                settings.env["FEISHU_APP_ID"],
                settings.env["FEISHU_APP_SECRET"],
                settings.env["FEISHU_CHAT_ID"],
                feishu_content,
                api_base_url=settings.env["FEISHU_API_BASE_URL"],
                timeout=request_timeout,
            ),
        ),
    ]

    for channel_name, configured, sender in delivery_plan:
        if not configured:
            results[channel_name] = build_channel_result(
                channel_name,
                configured=False,
                attempted=False,
                ok=False,
                detail="missing config",
            )
            continue
        if not send:
            results[channel_name] = build_channel_result(
                channel_name,
                configured=True,
                attempted=False,
                ok=False,
                detail="configured",
            )
            continue
        try:
            attempted_at = datetime.now().astimezone().isoformat(timespec="seconds")
            response = sender()
            ok = channel_response_succeeded(channel_name, response)
            detail = describe_channel_response(channel_name, response)
            responses[channel_name] = response
            results[channel_name] = build_channel_result(
                channel_name,
                configured=True,
                attempted=True,
                ok=ok,
                detail=detail,
                response=response,
                error_type=None if ok else classify_channel_error(channel_name, response, detail),
                attempted_at=attempted_at,
            )
        except Exception as exc:
            error_response = {"error": str(exc)}
            responses[channel_name] = error_response
            results[channel_name] = build_channel_result(
                channel_name,
                configured=True,
                attempted=True,
                ok=False,
                detail=str(exc),
                response=error_response,
                error_type=classify_channel_error(channel_name, error_response, str(exc)),
                attempted_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            )

    return summarize_delivery_results(results), responses


def render_reports(
    root_dir: Path,
    publication_mode: str = "",
    reviewer: str = "",
    review_note: str = "",
) -> tuple[list[str], dict[str, float], dict[str, object]]:
    settings = load_settings(root_dir)
    resolved_publication_mode = _resolve_publication_mode(settings, publication_mode)
    review = _resolve_review_metadata(
        settings,
        resolved_publication_mode,
        reviewer=reviewer,
        review_note=review_note,
    )
    generated_at = datetime.now().astimezone().isoformat()
    reports_dir = root_dir / "data" / "reports"
    state_dir = root_dir / "data" / "state"
    archive_dir = root_dir / "data" / "archives" / generated_at[:10]
    timings: dict[str, float] = {}

    with StageTimer("collection") as t:
        items, diagnostics = collect_all_items(settings)
    timings["collection"] = t.elapsed

    with StageTimer("dedup_score") as t:
        package = build_report_package(settings, items, diagnostics)
        # dedup + classify + score + AI pipeline 全部在 build_report_package 内完成
        package.summary_payload["meta"]["generated_at"] = generated_at
        package.summary_payload["meta"]["publication_mode"] = resolved_publication_mode
        package.summary_payload["meta"]["review"] = review
    timings["dedup_score"] = t.elapsed

    # 从 package 中提取 AI 阶段耗时（如果 ai_pipeline 有内部计时）
    timings["ai_total"] = 0.0  # 占位，AI 耗时已包含在 dedup_score 中（build_report_package 内部整体计时）

    with StageTimer("rendering") as t:
        summary_markdown = _compose_report_markdown(
            title=_report_title(resolved_publication_mode),
            generated_at=generated_at,
            payload=package.summary_payload,
        )
        summary_json = render_json_report(package.summary_payload)
        summary_html = render_html_report(
            title=_report_title(resolved_publication_mode),
            generated_at=generated_at,
            payload=package.summary_payload,
        )

        summary_md_path = reports_dir / "latest-summary.md"
        summary_json_path = reports_dir / "latest-summary.json"
        summary_html_path = reports_dir / "latest-summary.html"
        track_md_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.md"
        track_json_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.json"
        track_html_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.html"
        archive_md_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.md"
        archive_json_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.json"
        archive_html_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.html"
        track_archive_md_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.md"
        track_archive_json_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.json"
        track_archive_html_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.html"
        dedup_state_path = state_dir / "dedup-index.json"

        write_text(summary_md_path, summary_markdown)
        write_text(summary_json_path, summary_json)
        write_text(summary_html_path, summary_html)
        write_text(track_md_path, summary_markdown)
        write_text(track_json_path, summary_json)
        write_text(track_html_path, summary_html)
        write_text(archive_md_path, summary_markdown)
        write_text(archive_json_path, summary_json)
        write_text(archive_html_path, summary_html)
        write_text(track_archive_md_path, summary_markdown)
        write_text(track_archive_json_path, summary_json)
        write_text(track_archive_html_path, summary_html)
        write_text(dedup_state_path, render_json_report(package.dedup_state))

        generated_files = [
            str(summary_md_path),
            str(summary_json_path),
            str(summary_html_path),
            str(track_md_path),
            str(track_json_path),
            str(track_html_path),
            str(archive_md_path),
            str(archive_json_path),
            str(archive_html_path),
            str(track_archive_md_path),
            str(track_archive_json_path),
            str(track_archive_html_path),
            str(dedup_state_path),
        ]
        generated_files.extend(_write_domain_briefs(root_dir, generated_at, package, settings))
    timings["rendering"] = t.elapsed

    return generated_files, timings, {
        "external_enrichment": package.external_enrichment,
        "source_health": _summarize_source_health(diagnostics),
        "review": review,
    }


def run_backfill(
    root_dir: Path,
    target_date: str = "",
    publication_mode: str = "",
    reviewer: str = "",
    review_note: str = "",
) -> list[str]:
    settings = load_settings(root_dir)
    resolved_publication_mode = _resolve_publication_mode(settings, publication_mode)
    review = _resolve_review_metadata(
        settings,
        resolved_publication_mode,
        reviewer=reviewer,
        review_note=review_note,
    )
    generated_at = datetime.now().astimezone().isoformat()
    timings: dict[str, float] = {}

    archive_date = target_date.strip() if target_date.strip() else generated_at[:10]
    reports_dir = root_dir / "data" / "reports"
    state_dir = root_dir / "data" / "state"
    archive_dir = root_dir / "data" / "archives" / archive_date

    with StageTimer("collection") as t:
        items, diagnostics = collect_all_items(settings)
    timings["collection"] = t.elapsed

    with StageTimer("dedup_score") as t:
        package = build_report_package(settings, items, diagnostics)
        package.summary_payload["meta"]["generated_at"] = generated_at
        package.summary_payload["meta"]["publication_mode"] = resolved_publication_mode
        package.summary_payload["meta"]["review"] = review
    timings["dedup_score"] = t.elapsed
    timings["ai_total"] = 0.0  # AI pipeline 已在 build_report_package 内完成

    with StageTimer("rendering") as t:
        summary_markdown = _compose_report_markdown(
            title=_report_title(resolved_publication_mode, backfill=True),
            generated_at=generated_at,
            payload=package.summary_payload,
        )
        summary_json = render_json_report(package.summary_payload)
        summary_html = render_html_report(
            title=_report_title(resolved_publication_mode, backfill=True),
            generated_at=generated_at,
            payload=package.summary_payload,
        )

        summary_md_path = reports_dir / "latest-summary.md"
        summary_json_path = reports_dir / "latest-summary.json"
        summary_html_path = reports_dir / "latest-summary.html"
        track_md_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.md"
        track_json_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.json"
        track_html_path = reports_dir / f"{_summary_track_stem(resolved_publication_mode)}.html"
        archive_md_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.md"
        archive_json_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.json"
        archive_html_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.html"
        track_archive_md_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.md"
        track_archive_json_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.json"
        track_archive_html_path = archive_dir / f"{_archive_track_stem(generated_at, resolved_publication_mode)}.html"
        dedup_state_path = state_dir / "dedup-index.json"

        write_text(summary_md_path, summary_markdown)
        write_text(summary_json_path, summary_json)
        write_text(summary_html_path, summary_html)
        write_text(track_md_path, summary_markdown)
        write_text(track_json_path, summary_json)
        write_text(track_html_path, summary_html)
        write_text(archive_md_path, summary_markdown)
        write_text(archive_json_path, summary_json)
        write_text(archive_html_path, summary_html)
        write_text(track_archive_md_path, summary_markdown)
        write_text(track_archive_json_path, summary_json)
        write_text(track_archive_html_path, summary_html)
        write_text(dedup_state_path, render_json_report(package.dedup_state))

        generated_files = [
            str(summary_md_path),
            str(summary_json_path),
            str(summary_html_path),
            str(track_md_path),
            str(track_json_path),
            str(track_html_path),
            str(archive_md_path),
            str(archive_json_path),
            str(archive_html_path),
            str(track_archive_md_path),
            str(track_archive_json_path),
            str(track_archive_html_path),
            str(dedup_state_path),
        ]
        generated_files.extend(_write_domain_briefs(root_dir, generated_at, package, settings))
    timings["rendering"] = t.elapsed

    status = build_run_status(
        generated_files=_to_relative_paths(generated_files, root_dir),
        pushed=False,
        push_channel="",
        publication_mode=resolved_publication_mode,
        push_response={},
        delivery_results=_empty_delivery_results(),
        stage_status=package.summary_payload.get("stage_status", {}),
        source_stats={
            "collected_items": int(package.summary_payload.get("meta", {}).get("total_items", 0)),
            "report_topics": int(package.summary_payload.get("meta", {}).get("total_topics", 0)),
        },
        risk_level=str(package.summary_payload.get("risk_level", "low")),
        external_enrichment=package.external_enrichment,
        ai_metrics=package.summary_payload.get("ai_metrics", {}),
        source_health=_summarize_source_health(diagnostics),
        review=review,
        scheduler=_scheduler_context(settings),
        timings=timings,
    )
    status_path = root_dir / "data" / "state" / "run-status.json"
    write_text(status_path, render_json_report(status))
    generated_files.append(str(status_path))
    return generated_files


def run_once(
    root_dir: Path,
    publication_mode: str = "",
    reviewer: str = "",
    review_note: str = "",
) -> list[str]:
    settings = load_settings(root_dir)
    resolved_publication_mode = _resolve_publication_mode(settings, publication_mode)
    all_timings: dict[str, float] = {}
    delivery_results = _empty_delivery_results()

    with StageTimer("total") as total_timer:
        generated_files, render_timings, runtime_status = render_reports(
            root_dir,
            publication_mode=resolved_publication_mode,
            reviewer=reviewer,
            review_note=review_note,
        )
        all_timings.update(render_timings)
        external_enrichment = runtime_status.get("external_enrichment", {})
        source_health = runtime_status.get("source_health", {})
        review = runtime_status.get("review", {})

        summary_payload = _load_summary_payload(root_dir, publication_mode=resolved_publication_mode)
        pushed = False
        push_channel = ""
        push_response: dict[str, object] = {}

        with StageTimer("push_total") as push_timer:
            if settings.env["AUTO_PUSH_ENABLED"].lower() == "true":
                delivery_results, push_response = _collect_delivery_results(
                    root_dir,
                    settings,
                    send=True,
                    mode="full-report",
                    publication_mode=resolved_publication_mode,
                )
                pushed = bool(delivery_results["successful_channels"])
                push_channel = ",".join(delivery_results["successful_channels"])
            else:
                delivery_results, _ = _collect_delivery_results(
                    root_dir,
                    settings,
                    send=False,
                    mode="full-report",
                    publication_mode=resolved_publication_mode,
                )

        all_timings["push_total"] = push_timer.elapsed

    status = build_run_status(
        generated_files=_to_relative_paths(generated_files, root_dir),
        pushed=pushed,
        push_channel=push_channel,
        publication_mode=resolved_publication_mode,
        push_response=push_response,
        delivery_results=delivery_results,
        stage_status=summary_payload.get("stage_status", {}),
        source_stats={
            "collected_items": int(summary_payload.get("meta", {}).get("total_items", 0)),
            "report_topics": int(summary_payload.get("meta", {}).get("total_topics", 0)),
        },
        risk_level=str(summary_payload.get("risk_level", "low")),
        external_enrichment=external_enrichment,
        ai_metrics=summary_payload.get("ai_metrics", {}),
        source_health=source_health,
        review=review if isinstance(review, dict) else {},
        scheduler=_scheduler_context(settings),
        timings=all_timings,
    )
    status_path = root_dir / "data" / "state" / "run-status.json"
    write_text(status_path, render_json_report(status))
    generated_files.append(str(status_path))
    return generated_files


# ════════════════════════════════════════
# Phase 0: CI 三阶段命令
# ════════════════════════════════════════

def cmd_collect_only(root_dir: Path) -> list[str]:
    """CI Job 1: 采集 → 去重 → 分类 → 评分 → 构建候选主题 → 保存中间结果"""
    from auto_report.pipeline.dedup import deduplicate_items
    from auto_report.pipeline.scoring import score_topic
    from auto_report.pipeline.topic_builder import build_topic_candidates

    settings = load_settings(root_dir)
    generated_at = datetime.now().astimezone().isoformat()
    timings = {}

    with StageTimer("collection") as t:
        items, diagnostics = collect_all_items(settings)
    timings["collection"] = t.elapsed

    with StageTimer("dedup_score") as t:
        # 复用 analysis.py 中 build_report_package 的前半段逻辑
        unique_topics = deduplicate_items(items)
        candidates = build_topic_candidates(items)

        # 对每个去重后的主题打分（与 build_report_package 一致）
        scored_data = []
        for topic in unique_topics:
            from auto_report.domains.classifier import classify_topic
            domain_match = classify_topic(topic)
            tags = sorted({tag for item in topic.evidence_items for tag in item.tags if tag})
            scored_data.append({
                "title": topic.canonical_title,
                "url": topic.canonical_url,
                "score": score_topic(topic),
                "primary_domain": domain_match.primary_domain,
                "evidence_count": len(topic.evidence_items),
                "tags": tags,
            })

        # 按分数降序排列候选主题
        signal_scores = {(d["title"], d["url"]): d["score"] for d in scored_data}
        candidates.sort(
            key=lambda c: signal_scores.get((c.title, c.url), 0.0),
            reverse=True,
        )
    timings["dedup_score"] = t.elapsed

    # 序列化中间结果 (用 dataclass asdict)
    from dataclasses import asdict
    intermediate = {
        "generated_at": generated_at,
        "total_collected": len(items),
        "unique_topics": len(unique_topics),
        "candidates": [asdict(c) for c in candidates],
        "diagnostics": diagnostics,
        "timings": timings,
    }
    path = _save_intermediate(root_dir, intermediate)

    print(f"[collect-only] Collected {len(items)} items -> {len(unique_topics)} unique -> {len(candidates)} candidates")
    print(f"[collect-only] Intermediate saved to: {path}")
    print(f"[collect-only] Timings: {timings}")
    return [path]


def cmd_analyze_only(root_dir: Path) -> list[str]:
    """CI Job 2: 加载中间结果 -> AI三阶段分析 -> 保存分析结果"""
    from auto_report.models.records import TopicCandidate
    from auto_report.pipeline.ai_pipeline import run_staged_ai_pipeline
    from auto_report.pipeline.prompt_loader import load_ai_readings

    settings = load_settings(root_dir)
    timings = {}

    with StageTimer("load") as t:
        intermediate = _load_intermediate(root_dir)
    timings["load"] = t.elapsed

    # 反序列化 candidates
    raw_candidates = intermediate.get("candidates", [])
    candidates = [TopicCandidate(**c) for c in raw_candidates]

    ai_enabled = is_llm_enabled()
    ai_readings = load_ai_readings(root_dir)

    with StageTimer("ai_total") as t:
        result = run_staged_ai_pipeline(
            candidates=candidates,
            ai_readings=ai_readings,
            ai_enabled=ai_enabled,
        )
    timings["ai_total"] = t.elapsed

    meta = {
        "analyzed_at": datetime.now().astimezone().isoformat(),
        "candidate_count": len(candidates),
        "analysis_count": len(result["analyses"]),
        "stage_status": result["stage_status"],
        "timings": timings,
    }
    path = _save_analysis_result(root_dir, result, meta=meta)

    stage_status = result.get("stage_status", {})
    print(f"[analyze-only] Analyzed {len(result['analyses'])} topics | Status: {stage_status}")
    print(f"[analyze-only] AI total time: {timings['ai_total']}s | Saved to: {path}")
    return [path]


def cmd_render_and_push(
    root_dir: Path,
    publication_mode: str = "",
    reviewer: str = "",
    review_note: str = "",
) -> list[str]:
    """CI Job 3: 渲染 MD+JSON+HTML -> 三通道推送 -> 归档"""
    return run_once(
        root_dir,
        publication_mode=publication_mode,
        reviewer=reviewer,
        review_note=review_note,
    )


def cmd_diagnose_delivery(root_dir: Path, send: bool = False, mode: str = "canary") -> dict[str, object]:
    settings = load_settings(root_dir)
    summary, _ = _collect_delivery_results(root_dir, settings, send=send, mode=mode)
    for name, item in summary["channels"].items():
        print(
            f"[{name}] status={item['status']} configured={item['configured']} "
            f"attempted={item['attempted']} error_type={item['error_type']} detail={item['detail']}"
        )
    return summary


def cmd_build_ops_dashboard(root_dir: Path) -> Path:
    return build_ops_dashboard(root_dir)


def cmd_build_review_queue(root_dir: Path) -> Path:
    from auto_report.pipeline.review_queue import build_review_issue_candidates

    payload = _load_summary_payload(root_dir)
    issues = build_review_issue_candidates(payload)
    output_dir = root_dir / "out" / "review-queue"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "review-issues.json"
    output_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().astimezone().isoformat(),
                "count": len(issues),
                "issues": issues,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[ReviewQueue] Built at {output_path}")
    return output_path


def cmd_evaluate_prompts(root_dir: Path, dataset_path: str) -> Path:
    from auto_report.pipeline.prompt_evaluator import evaluate_prompt_dataset

    return evaluate_prompt_dataset(root_dir, Path(dataset_path))


# ════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════

def _load_dedup_state(root_dir: Path) -> dict:
    """加载去重状态"""
    path = root_dir / "data" / "state" / "dedup-index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
