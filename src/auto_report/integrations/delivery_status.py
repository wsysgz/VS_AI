from __future__ import annotations


AUTH_KEYWORDS = (
    "unauthorized",
    "invalid token",
    "auth failed",
    "401",
)
PERMISSION_KEYWORDS = (
    "forbidden",
    "permission denied",
    "insufficient permission",
    "not enough rights",
    "403",
)
NETWORK_KEYWORDS = (
    "timeout",
    "timed out",
    "connection",
    "network",
    "dns",
    "ssl",
    "temporarily unavailable",
)
FORMAT_KEYWORDS = (
    "bad request",
    "message is too long",
    "can't parse",
    "invalid markdown",
    "invalid payload",
    "400",
    "422",
)


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


def _collect_error_text(response: object, detail: str = "") -> str:
    texts: list[str] = []
    if detail:
        texts.append(detail)

    for item in _response_items(response):
        for key in ("error", "description", "msg", "message"):
            value = item.get(key)
            if isinstance(value, str) and value:
                texts.append(value)
        code = item.get("code")
        if code is not None:
            texts.append(str(code))
        status_code = item.get("status_code")
        if status_code is not None:
            texts.append(str(status_code))

    return " ".join(texts).lower()


def classify_channel_error(name: str, response: object, detail: str = "") -> str:
    text = _collect_error_text(response, detail=detail)
    if not text:
        return "unknown"

    if any(keyword in text for keyword in AUTH_KEYWORDS):
        return "auth"
    if any(keyword in text for keyword in PERMISSION_KEYWORDS):
        return "permission"
    if any(keyword in text for keyword in NETWORK_KEYWORDS):
        return "network"
    if any(keyword in text for keyword in FORMAT_KEYWORDS):
        return "format"
    return "unknown"


def build_channel_result(
    name: str,
    configured: bool,
    attempted: bool,
    ok: bool,
    detail: str = "",
    response: object | None = None,
    error_type: str | None = None,
    attempted_at: str | None = None,
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
        "error_type": error_type,
        "attempted_at": attempted_at,
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
