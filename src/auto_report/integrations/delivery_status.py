from __future__ import annotations


def _response_items(response: object) -> list[dict[str, object]]:
    if isinstance(response, dict):
        return [response]
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    return []


def channel_response_succeeded(name: str, response: object) -> bool:
    items = _response_items(response)
    if not items:
        return False

    if name == "pushplus":
        return bool(items[0].get("code") in (0, 200))
    if name == "telegram":
        return all(bool(item.get("ok")) for item in items)
    if name == "feishu":
        return all(item.get("code") == 0 for item in items)
    return False


def describe_channel_response(name: str, response: object) -> str:
    items = _response_items(response)
    if not items:
        return ""

    first = items[0]
    if isinstance(first.get("error"), str):
        return str(first["error"])

    if name == "pushplus":
        code = first.get("code")
        msg = first.get("msg")
        return f"code={code}" if not msg else f"code={code} {msg}"

    if name == "telegram":
        description = first.get("description")
        if isinstance(description, str) and description:
            return description
        return f"{len(items)} message(s)"

    if name == "feishu":
        msg = first.get("msg")
        if isinstance(msg, str) and msg:
            return msg
        return f"{len(items)} message(s)"

    return ""


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
