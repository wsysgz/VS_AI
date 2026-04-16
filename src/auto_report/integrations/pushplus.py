from __future__ import annotations

import time
from typing import Any

import requests

CLAWBOT_UNVERIFIED_NOTE = (
    "ClawBot accepted by API only; final delivery requires active chat context "
    "and cannot be verified without PUSHPLUS_SECRETKEY."
)
def build_pushplus_payload(
    token: str,
    title: str,
    content: str,
    channel: str = "",
    template: str = "markdown",
    secret_key: str = "",
) -> dict[str, str]:
    resolved_template = template
    if channel == "clawbot" and template == "markdown":
        resolved_template = "txt"

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": resolved_template,
    }
    if channel:
        payload["channel"] = channel
    return payload


def _decode_pushplus_response(response: requests.Response, error_prefix: str) -> dict[str, Any]:
    response.raise_for_status()
    data = response.json()
    if data.get("code") not in (0, 200):
        raise RuntimeError(f"{error_prefix}: {data}")
    return data


def _fetch_openapi_access_key(token: str, secret_key: str, base_url: str, timeout: int) -> str:
    data = _decode_pushplus_response(
        requests.post(
            f"{base_url.rstrip('/')}/api/common/openApi/getAccessKey",
            json={"token": token, "secretKey": secret_key},
            timeout=timeout,
        ),
        "PushPlus getAccessKey failed",
    )
    payload = data.get("data", {})
    access_key = ""
    if isinstance(payload, dict):
        access_key = str(payload.get("accessKey", "")).strip()
    if not access_key:
        raise RuntimeError("PushPlus getAccessKey returned no accessKey")
    return access_key


def _fetch_openapi_data(access_key: str, path: str, base_url: str, timeout: int) -> dict[str, Any]:
    data = _decode_pushplus_response(
        requests.get(
            f"{base_url.rstrip('/')}{path}",
            headers={"access-key": access_key},
            timeout=timeout,
        ),
        "PushPlus openApi request failed",
    )
    payload = data.get("data", {})
    return payload if isinstance(payload, dict) else {}


def _verify_clawbot_delivery(
    token: str,
    short_code: str,
    secret_key: str,
    base_url: str,
    timeout: int,
) -> dict[str, Any]:
    if not secret_key:
        return {
            "available": False,
            "reason": "missing_secret_key",
            "note": CLAWBOT_UNVERIFIED_NOTE,
        }

    try:
        access_key = _fetch_openapi_access_key(token, secret_key, base_url=base_url, timeout=timeout)
        bot_info = _fetch_openapi_data(access_key, "/api/open/clawBot/botInfo", base_url=base_url, timeout=timeout)
    except Exception as exc:
        return {
            "available": False,
            "reason": "openapi_unavailable",
            "note": f"ClawBot verification unavailable: {exc}",
        }

    if int(bot_info.get("haveContextToken", 0) or 0) != 1:
        raise RuntimeError(
            "ClawBot is not activated: missing active chat context. "
            "Send a message to the WeChat ClawBot and confirm activation in PushPlus."
        )

    delivery: dict[str, Any] = {}
    if short_code:
        try:
            for _ in range(3):
                delivery = _fetch_openapi_data(
                    access_key,
                    f"/api/open/message/sendMessageResult?shortCode={short_code}",
                    base_url=base_url,
                    timeout=timeout,
                )
                status = int(delivery.get("status", -1) or -1)
                if status in (2, 3):
                    break
                time.sleep(1)
        except Exception as exc:
            return {
                "available": False,
                "reason": "send_result_unavailable",
                "note": f"ClawBot verification unavailable: {exc}",
                "bot_info": bot_info,
            }

        if int(delivery.get("status", -1) or -1) == 3:
            error_message = str(delivery.get("errorMessage", "")).strip()
            if error_message:
                raise RuntimeError(f"ClawBot delivery failed: {error_message}")
            raise RuntimeError("ClawBot delivery failed")

    return {
        "available": True,
        "bot_info": bot_info,
        "delivery": delivery,
    }


def send_pushplus(
    token: str,
    title: str,
    content: str,
    channel: str = "",
    template: str = "markdown",
    secret_key: str = "",
    base_url: str = "https://www.pushplus.plus",
    timeout: int = 20,
) -> dict[str, Any]:
    response = requests.post(
        f"{base_url.rstrip('/')}/send",
        json=build_pushplus_payload(token, title, content, channel=channel, template=template, secret_key=secret_key),
        timeout=timeout,
    )
    data = _decode_pushplus_response(response, "PushPlus send failed")
    if channel == "clawbot":
        short_code = str(data.get("data", "")).strip()
        data["verification"] = _verify_clawbot_delivery(
            token,
            short_code=short_code,
            secret_key=secret_key,
            base_url=base_url,
            timeout=timeout,
        )
    return data
