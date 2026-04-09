from __future__ import annotations

from datetime import datetime, timezone
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

    return summary


def build_run_status(
    generated_files: list[str],
    pushed: bool,
    push_channel: str = "",
    push_response: dict[str, Any] | None = None,
    stage_status: dict[str, str] | None = None,
    source_stats: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
        "push_channel": push_channel,
        "push_response": _summarize_push_response(push_response),
        "stage_status": stage_status or {},
        "source_stats": source_stats or {},
    }
