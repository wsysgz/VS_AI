from __future__ import annotations

import requests


def build_pushplus_payload(token: str, title: str, content: str) -> dict[str, str]:
    return {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",
    }


def send_pushplus(token: str, title: str, content: str) -> dict[str, object]:
    response = requests.post(
        "https://www.pushplus.plus/send",
        json=build_pushplus_payload(token, title, content),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()
