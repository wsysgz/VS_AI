from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from auto_report.integrations.feishu import send_feishu_messages
from auto_report.integrations.pushplus import send_pushplus
from auto_report.integrations.telegram import send_telegram_messages
from auto_report.outputs.archive import write_text
from auto_report.outputs.renderers import (
    render_html_report,
    render_json_report,
    render_markdown_report,
    render_telegram_notification,
    render_text_notification,
)
from auto_report.pipeline.analysis import build_report_package
from auto_report.pipeline.run_once import build_run_status, _to_relative_paths
from auto_report.settings import load_settings
from auto_report.sources.collector import collect_all_items


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


def _build_feishu_notification(root_dir: Path, settings) -> str:
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


def render_reports(root_dir: Path) -> tuple[list[str], dict[str, float]]:
    settings = load_settings(root_dir)
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
    timings["dedup_score"] = t.elapsed

    # 从 package 中提取 AI 阶段耗时（如果 ai_pipeline 有内部计时）
    timings["ai_total"] = 0.0  # 占位，AI 耗时已包含在 dedup_score 中（build_report_package 内部整体计时）

    with StageTimer("rendering") as t:
        summary_markdown = _compose_report_markdown(
            title="自动情报快报",
            generated_at=generated_at,
            payload=package.summary_payload,
        )
        summary_json = render_json_report(package.summary_payload)
        summary_html = render_html_report(
            title="自动情报快报",
            generated_at=generated_at,
            payload=package.summary_payload,
        )

        summary_md_path = reports_dir / "latest-summary.md"
        summary_json_path = reports_dir / "latest-summary.json"
        summary_html_path = reports_dir / "latest-summary.html"
        archive_md_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.md"
        archive_json_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.json"
        archive_html_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.html"
        dedup_state_path = state_dir / "dedup-index.json"

        write_text(summary_md_path, summary_markdown)
        write_text(summary_json_path, summary_json)
        write_text(summary_html_path, summary_html)
        write_text(archive_md_path, summary_markdown)
        write_text(archive_json_path, summary_json)
        write_text(archive_html_path, summary_html)
        write_text(dedup_state_path, render_json_report(package.dedup_state))

        generated_files = [
            str(summary_md_path),
            str(summary_json_path),
            str(summary_html_path),
            str(archive_md_path),
            str(archive_json_path),
            str(archive_html_path),
            str(dedup_state_path),
        ]
        generated_files.extend(_write_domain_briefs(root_dir, generated_at, package, settings))
    timings["rendering"] = t.elapsed

    return generated_files, timings


def run_backfill(root_dir: Path, target_date: str = "") -> list[str]:
    settings = load_settings(root_dir)
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
    timings["dedup_score"] = t.elapsed
    timings["ai_total"] = 0.0  # AI pipeline 已在 build_report_package 内完成

    with StageTimer("rendering") as t:
        summary_markdown = _compose_report_markdown(
            title="自动情报快报（补报）",
            generated_at=generated_at,
            payload=package.summary_payload,
        )
        summary_json = render_json_report(package.summary_payload)
        summary_html = render_html_report(
            title="自动情报快报（补报）",
            generated_at=generated_at,
            payload=package.summary_payload,
        )

        summary_md_path = reports_dir / "latest-summary.md"
        summary_json_path = reports_dir / "latest-summary.json"
        summary_html_path = reports_dir / "latest-summary.html"
        archive_md_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.md"
        archive_json_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.json"
        archive_html_path = archive_dir / f"{generated_at.replace(':', '-')}-summary.html"
        dedup_state_path = state_dir / "dedup-index.json"

        write_text(summary_md_path, summary_markdown)
        write_text(summary_json_path, summary_json)
        write_text(summary_html_path, summary_html)
        write_text(archive_md_path, summary_markdown)
        write_text(archive_json_path, summary_json)
        write_text(archive_html_path, summary_html)
        write_text(dedup_state_path, render_json_report(package.dedup_state))

        generated_files = [
            str(summary_md_path),
            str(summary_json_path),
            str(summary_html_path),
            str(archive_md_path),
            str(archive_json_path),
            str(archive_html_path),
            str(dedup_state_path),
        ]
        generated_files.extend(_write_domain_briefs(root_dir, generated_at, package, settings))
    timings["rendering"] = t.elapsed

    status = build_run_status(
        generated_files=_to_relative_paths(generated_files, root_dir),
        pushed=False,
        push_channel="",
        push_response={},
        stage_status=package.summary_payload.get("stage_status", {}),
        source_stats={
            "collected_items": int(package.summary_payload.get("meta", {}).get("total_items", 0)),
            "filtered_topics": int(package.summary_payload.get("meta", {}).get("total_topics", 0)),
        },
        timings=timings,
    )
    status_path = root_dir / "data" / "state" / "run-status.json"
    write_text(status_path, render_json_report(status))
    generated_files.append(str(status_path))
    return generated_files


def run_once(root_dir: Path) -> list[str]:
    settings = load_settings(root_dir)
    all_timings: dict[str, float] = {}

    with StageTimer("total") as total_timer:
        generated_files, render_timings = render_reports(root_dir)
        all_timings.update(render_timings)

        summary_payload = _load_summary_payload(root_dir)
        pushed = False
        push_channel = ""
        push_response: dict[str, object] = {}

        with StageTimer("push_total") as push_timer:
            if settings.env["AUTO_PUSH_ENABLED"].lower() == "true":
                text_notification = _build_text_notification(root_dir, settings)
                notification_results: dict[str, object] = {}

                if settings.env["PUSHPLUS_TOKEN"]:
                    try:
                        push_channel = settings.env["PUSHPLUS_CHANNEL"]
                        push_response = send_pushplus(
                            settings.env["PUSHPLUS_TOKEN"],
                            "自动情报快报",
                            text_notification if push_channel == "clawbot" else (root_dir / "data" / "reports" / "latest-summary.md").read_text(encoding="utf-8"),
                            channel=push_channel,
                            template="txt" if push_channel == "clawbot" else "markdown",
                            secret_key=settings.env.get("PUSHPLUS_SECRETKEY", ""),
                        )
                        notification_results["pushplus"] = push_response
                    except Exception as e:
                        notification_results["pushplus"] = {"error": str(e)}

                if settings.env["TELEGRAM_BOT_TOKEN"] and settings.env["TELEGRAM_CHAT_ID"]:
                    try:
                        notification_results["telegram"] = send_telegram_messages(
                            settings.env["TELEGRAM_BOT_TOKEN"],
                            settings.env["TELEGRAM_CHAT_ID"],
                            _build_telegram_notification(root_dir, settings),
                        )
                    except Exception as e:
                        notification_results["telegram"] = {"error": str(e)}

                if settings.env["FEISHU_APP_ID"] and settings.env["FEISHU_APP_SECRET"] and settings.env["FEISHU_CHAT_ID"]:
                    try:
                        notification_results["feishu"] = send_feishu_messages(
                            settings.env["FEISHU_APP_ID"],
                            settings.env["FEISHU_APP_SECRET"],
                            settings.env["FEISHU_CHAT_ID"],
                            _build_feishu_notification(root_dir, settings),
                        )
                    except Exception as e:
                        notification_results["feishu"] = {"error": str(e)}

                if notification_results:
                    push_response = notification_results
                    pushed = True

        all_timings["push_total"] = push_timer.elapsed

    status = build_run_status(
        generated_files=_to_relative_paths(generated_files, root_dir),
        pushed=pushed,
        push_channel=push_channel,
        push_response=push_response,
        stage_status=summary_payload.get("stage_status", {}),
        source_stats={
            "collected_items": int(summary_payload.get("meta", {}).get("total_items", 0)),
            "filtered_topics": int(summary_payload.get("meta", {}).get("total_topics", 0)),
        },
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

    ai_enabled = bool(settings.env.get("DEEPSEEK_API_KEY"))
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


def cmd_render_and_push(root_dir: Path) -> list[str]:
    """CI Job 3: 渲染 MD+JSON+HTML -> 三通道推送 -> 归档"""
    return run_once(root_dir)


# ════════════════════════════════════════
# 内部辅助
# ════════════════════════════════════════

def _load_dedup_state(root_dir: Path) -> dict:
    """加载去重状态"""
    path = root_dir / "data" / "state" / "dedup-index.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
