from __future__ import annotations

import hashlib
import time
from typing import Any

import requests


def _sign_token(token: str, secret_key: str) -> str:
    """PushPlus token + secretkey 签名算法：md5(token+secretkey+timestamp)"""
    timestamp = str(int(time.time()))
    raw = f"{token}{secret_key}{timestamp}"
    signature = hashlib.md5(raw.encode()).hexdigest()
    return f"{token}.{signature}.{timestamp}"


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

    # 有 secretkey 时使用签名 token
    effective_token = _sign_token(token, secret_key) if secret_key else token

    payload = {
        "token": effective_token,
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
    secret_key: str = "",
) -> dict[str, Any]:
    response = requests.post(
        "https://www.pushplus.plus/send",
        json=build_pushplus_payload(token, title, content, channel=channel, template=template, secret_key=secret_key),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
