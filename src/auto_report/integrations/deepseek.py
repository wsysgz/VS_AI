from __future__ import annotations

from typing import Any
import os

import requests


def build_deepseek_payload(prompt: str) -> dict[str, Any]:
    return {
        "model": os.environ.get("AI_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(os.environ.get("AI_TEMPERATURE", "0.2")),
    }


def summarize_with_deepseek(prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    response = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=build_deepseek_payload(prompt),
        timeout=40,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
