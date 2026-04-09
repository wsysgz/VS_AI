from __future__ import annotations

from typing import Any

import requests


def build_pushplus_payload(
    token: str,
    title: str,
    content: str,
    channel: str = "",
) -> dict[str, str]:
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
    }
    if channel:
        payload["channel"] = channel
    return payload


def send_pushplus(
    token: str,
    title: str,
    content: str,
    channel: str = "",
) -> dict[str, Any]:
    response = requests.post(
        "https://www.pushplus.plus/send",
        json=build_pushplus_payload(token, title, content, channel=channel),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
