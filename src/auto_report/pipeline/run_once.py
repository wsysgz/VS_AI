from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _summarize_telegram_response(push_response: object) -> dict[str, object]:
    if isinstance(push_response, dict):
        responses = [push_response]
    elif isinstance(push_response, list):
        responses = [item for item in push_response if isinstance(item, dict)]
    else:
        return {}

    message_ids: list[int] = []
    all_ok = True
    description = ""

    for item in responses:
        all_ok = all_ok and bool(item.get("ok", False))
        if not description and isinstance(item.get("description"), str):
            description = item["description"]

        result = item.get("result")
        if isinstance(result, dict) and isinstance(result.get("message_id"), int):
            message_ids.append(result["message_id"])

    summary: dict[str, object] = {
        "ok": all_ok,
        "messages_sent": len(responses),
        "message_ids": message_ids,
    }
    if description:
        summary["description"] = description
    return summary


def _summarize_feishu_response(push_response: object) -> dict[str, object]:
    if isinstance(push_response, dict):
        responses = [push_response]
    elif isinstance(push_response, list):
        responses = [item for item in push_response if isinstance(item, dict)]
    else:
        return {}

    message_ids: list[str] = []
    all_ok = True
    description = ""

    for item in responses:
        all_ok = all_ok and item.get("code") == 0
        if not description and isinstance(item.get("msg"), str):
            description = item["msg"]

        data = item.get("data")
        if isinstance(data, dict) and isinstance(data.get("message_id"), str):
            message_ids.append(data["message_id"])

    summary: dict[str, object] = {
        "ok": all_ok,
        "messages_sent": len(responses),
        "message_ids": message_ids,
    }
    if description:
        summary["description"] = description
    return summary


def _summarize_push_response(push_response: dict[str, Any] | None) -> dict[str, object]:
    if not push_response:
        return {}

    summary: dict[str, object] = {}
    pushplus_response = push_response.get("pushplus")
    if isinstance(pushplus_response, dict):
        summary["pushplus"] = {
            key: pushplus_response[key]
            for key in ("code", "msg", "data")
            if key in pushplus_response
        }

    telegram_response = push_response.get("telegram")
    telegram_summary = _summarize_telegram_response(telegram_response)
    if telegram_summary:
        summary["telegram"] = telegram_summary

    feishu_response = push_response.get("feishu")
    feishu_summary = _summarize_feishu_response(feishu_response)
    if feishu_summary:
        summary["feishu"] = feishu_summary

    return summary


def _to_relative_paths(files: list[str], root_dir: Path) -> list[str]:
    """将绝对路径列表转换为相对于 root_dir 的路径（用于 run-status.json）"""
    # 统一使用正斜杠比较，避免 Windows 路径分隔符不一致
    root_normalized = str(root_dir).replace("\\", "/").rstrip("/").lower()
    result = []
    for f in files:
        f_normalized = str(f).replace("\\", "/").lower()
        # 检查是否以 root + "/" 开头
        if f_normalized.startswith(root_normalized + "/"):
            # 从 root 之后截取，保持正斜杠
            rel = str(f).replace("\\", "/")[len(root_normalized) + 1:]
            result.append(rel)
        else:
            result.append(str(f).replace("\\", "/"))
    return result


def _default_external_enrichment_status() -> dict[str, object]:
    return {
        "enabled": False,
        "max_signals": 0,
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "budget_used": 0,
        "success_rate": 0.0,
        "circuit_open": False,
        "reasons": [],
    }


def _default_ai_metrics_status() -> dict[str, object]:
    return {
        "provider": "",
        "model": "",
        "calls": 0,
        "token_usage": {
            "prompt": 0,
            "completion": 0,
            "total": 0,
        },
        "latency_seconds": 0.0,
        "fallback_stages": [],
    }


def _default_source_health_status() -> dict[str, object]:
    return {
        "total": 0,
        "not_found": 0,
        "timeout": 0,
        "request_error": 0,
        "other": 0,
        "samples": [],
    }


def _default_review_status() -> dict[str, str]:
    return {
        "reviewer": "",
        "review_note": "",
    }


def _default_source_registry_status() -> dict[str, object]:
    return {}


def _default_source_governance_status() -> dict[str, object]:
    return {
        "summary": {
            "manual_review_count": 0,
            "rsshub_candidate_count": 0,
            "changedetection_candidate_count": 0,
            "replacement_candidate_count": 0,
        },
        "manual_review": [],
        "rsshub_candidates": [],
        "changedetection_candidates": [],
        "replacement_candidates": [],
    }


def build_run_status(
    generated_files: list[str],
    pushed: bool,
    generated_at: str = "",
    push_channel: str = "",
    publication_mode: str = "auto",
    push_response: dict[str, Any] | None = None,
    delivery_results: dict[str, Any] | None = None,
    stage_status: dict[str, str] | None = None,
    source_stats: dict[str, int] | None = None,
    scheduler: dict[str, Any] | None = None,
    timings: dict[str, float] | None = None,
    risk_level: str = "low",
    external_enrichment: dict[str, Any] | None = None,
    ai_metrics: dict[str, Any] | None = None,
    source_health: dict[str, Any] | None = None,
    source_registry: dict[str, Any] | None = None,
    source_governance: dict[str, Any] | None = None,
    review: dict[str, str] | None = None,
    error: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
        "push_channel": push_channel,
        "publication_mode": "reviewed" if str(publication_mode).strip().lower() == "reviewed" else "auto",
        "push_response": _summarize_push_response(push_response),
        "delivery_results": delivery_results or {
            "channels": {},
            "successful_channels": [],
            "failed_channels": [],
            "skipped_channels": [],
        },
        "stage_status": stage_status or {},
        "source_stats": source_stats or {},
        "risk_level": risk_level,
        "external_enrichment": external_enrichment or _default_external_enrichment_status(),
        "ai_metrics": ai_metrics or _default_ai_metrics_status(),
        "source_health": source_health or _default_source_health_status(),
        "source_registry": source_registry or _default_source_registry_status(),
        "source_governance": source_governance or _default_source_governance_status(),
        "review": review or _default_review_status(),
        "scheduler": scheduler or {
            "trigger_kind": "manual",
            "compensation_run": False,
        },
    }
    if timings:
        payload["timings"] = timings
        payload["total_elapsed"] = round(sum(timings.values()), 2)
    if error:
        payload["error"] = error
    return payload
