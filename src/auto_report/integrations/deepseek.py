from __future__ import annotations

import os
import time
import requests


def build_deepseek_payload(prompt: str) -> dict[str, object]:
    return {
        "model": os.environ.get("AI_MODEL", "deepseek-chat"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(os.environ.get("AI_TEMPERATURE", "0.2")),
    }


# Session 复用 — TCP 连接保持，减少每次 ~100ms 握手开销
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})


def summarize_with_deepseek(prompt: str) -> str:
    """带重试和指数退避的 DeepSeek 调用
    
    重试策略：
    - 最多 3 次重试
    - 网络超时/连接错误: 指数退避 1s -> 2s -> 4s
    - HTTP 429 Rate Limit: 等 60s 后重试
    - 超时时间递增: 45s -> 55s -> 65s
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    max_retries = 3

    for attempt in range(max_retries):
        try:
            base_timeout = 45 + attempt * 10  # 45s, 55s, 65s
            response = _session.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                json=build_deepseek_payload(prompt),
                timeout=base_timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)
                continue
            raise RuntimeError(f"DeepSeek API timeout after {max_retries} attempts") from exc

        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            # Rate limited: 等60秒后重试
            if status_code == 429 and attempt < max_retries - 1:
                time.sleep(60)
                continue
            raise

        except requests.exceptions.ConnectionError as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise RuntimeError(f"DeepSeek API connection failed after {max_retries} attempts") from exc

    raise RuntimeError(f"DeepSeek API failed after {max_retries} attempts")
