from __future__ import annotations

from typing import Any

import requests

TELEGRAM_MAX_TEXT_LENGTH = 4096


def build_telegram_payload(chat_id: str, text: str) -> dict[str, object]:
    return {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }


def split_telegram_text(text: str, max_length: int = TELEGRAM_MAX_TEXT_LENGTH) -> list[str]:
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


def send_telegram_message(
    token: str,
    chat_id: str,
    text: str,
    api_base_url: str = "https://api.telegram.org",
    timeout: int = 20,
) -> dict[str, Any]:
    response = requests.post(
        f"{api_base_url.rstrip('/')}/bot{token}/sendMessage",
        json=build_telegram_payload(chat_id, text),
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok", False):
        raise RuntimeError(str(data.get("description", "telegram send failed")))
    return data


def send_telegram_messages(
    token: str,
    chat_id: str,
    text: str,
    api_base_url: str = "https://api.telegram.org",
    timeout: int = 20,
) -> list[dict[str, Any]]:
    return [
        send_telegram_message(token, chat_id, chunk, api_base_url=api_base_url, timeout=timeout)
        for chunk in split_telegram_text(text)
    ]
