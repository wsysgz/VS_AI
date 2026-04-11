from __future__ import annotations


def build_channel_result(
    name: str,
    configured: bool,
    attempted: bool,
    ok: bool,
    detail: str = "",
    response: object | None = None,
) -> dict[str, object]:
    status = "skipped"
    if configured and attempted and ok:
        status = "ok"
    elif configured and attempted and not ok:
        status = "error"
    elif configured and not attempted:
        status = "skipped"
    return {
        "name": name,
        "configured": configured,
        "attempted": attempted,
        "ok": ok,
        "status": status,
        "detail": detail,
        "response": response,
    }


def summarize_delivery_results(results: dict[str, dict[str, object]]) -> dict[str, object]:
    successful = [name for name, item in results.items() if item.get("status") == "ok"]
    failed = [name for name, item in results.items() if item.get("status") == "error"]
    skipped = [name for name, item in results.items() if item.get("status") == "skipped"]
    return {
        "channels": results,
        "successful_channels": successful,
        "failed_channels": failed,
        "skipped_channels": skipped,
    }
