from __future__ import annotations

from typing import Any

import json

import requests

FEISHU_MAX_TEXT_LENGTH = 4096


def build_feishu_payload(receive_id: str, text: str) -> dict[str, object]:
    """Build message body for Feishu bot send API."""
    return {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }


def split_feishu_text(text: str, max_length: int = FEISHU_MAX_TEXT_LENGTH) -> list[str]:
    """Split long text into chunks that fit within Feishu message length limits."""
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + max_length, len(text))
        split_at = end

        if end < len(text):
            for separator in ("\n\n", "\n", " "):
                candidate = text.rfind(separator, start, end)
                if candidate > start:
                    split_at = candidate + len(separator)
                    break

        if split_at <= start:
            split_at = end

        chunks.append(text[start:split_at])
        start = split_at

    return chunks


def send_feishu_message(
    app_id: str,
    app_secret: str,
    receive_id: str,
    text: str,
    api_base_url: str = "https://open.feishu.cn",
    timeout: int = 20,
) -> dict[str, Any]:
    """Send a single message to a Feishu group chat via bot API."""
    base_url = api_base_url.rstrip("/")
    # 1. Get tenant_access_token
    token_resp = requests.post(
        f"{base_url}/open-apis/auth/v3/tenant_access_token/internal",
        json={
            "app_id": app_id,
            "app_secret": app_secret,
        },
        timeout=timeout,
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()
    if token_data.get("code") != 0:
        raise RuntimeError(f"Feishu auth failed: {token_data}")
    access_token = token_data["tenant_access_token"]

    # 2. Send message
    response = requests.post(
        f"{base_url}/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {access_token}"},
        json=build_feishu_payload(receive_id, text),
        timeout=timeout,
    )
    response.raise_for_status()
    send_data = response.json()
    if send_data.get("code") != 0:
        raise RuntimeError(f"Feishu send failed: {send_data}")
    return send_data


def send_feishu_messages(
    app_id: str,
    app_secret: str,
    receive_id: str,
    text: str,
    api_base_url: str = "https://open.feishu.cn",
    timeout: int = 20,
) -> list[dict[str, Any]]:
    """Send possibly long text as multiple messages (auto-split)."""
    return [
        send_feishu_message(
            app_id,
            app_secret,
            receive_id,
            chunk,
            api_base_url=api_base_url,
            timeout=timeout,
        )
        for chunk in split_feishu_text(text)
    ]
