from __future__ import annotations

from typing import Any

import requests


def build_pushplus_payload(
    token: str,
    title: str,
    content: str,
    channel: str = "",
    template: str = "markdown",
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


def send_pushplus(
    token: str,
    title: str,
    content: str,
    channel: str = "",
    template: str = "markdown",
) -> dict[str, Any]:
    response = requests.post(
        "https://www.pushplus.plus/send",
        json=build_pushplus_payload(token, title, content, channel=channel, template=template),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
