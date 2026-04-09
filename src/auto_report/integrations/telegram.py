from __future__ import annotations

from typing import Any

import requests


def build_telegram_payload(chat_id: str, text: str) -> dict[str, object]:
    return {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }


def send_telegram_message(token: str, chat_id: str, text: str) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json=build_telegram_payload(chat_id, text),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
