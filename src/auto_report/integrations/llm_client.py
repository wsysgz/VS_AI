"""通用 LLM 客户端 — 支持 OpenAI 兼容接口（DeepSeek / OpenAI / 本地部署等）

通过环境变量切换后端，无需改代码：
  AI_PROVIDER=deepseek  (默认)
  AI_PROVIDER=openai
  AI_BASE_URL=https://api.deepseek.com
  AI_MODEL=deepseek-chat
  DEEPSEEK_API_KEY / OPENAI_API_KEY
"""

from __future__ import annotations

import os
import threading
import time

import requests


# ── Provider 配置注册表 ──────────────────────────────

# 每个 provider 的默认配置
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
}


def _stage_prefix(stage: str | None = None) -> str:
    normalized = str(stage or "").strip().upper()
    return f"{normalized}_" if normalized else ""


def _resolve_api_key(provider: str, defaults: dict[str, str], stage: str | None = None) -> tuple[str, str]:
    prefix = _stage_prefix(stage)
    stage_ai_key_env = f"{prefix}AI_API_KEY" if prefix else ""

    if provider in _PROVIDER_DEFAULTS:
        env_candidates = []
        if prefix:
            env_candidates.append(f"{prefix}{defaults['key_env']}")
        if stage_ai_key_env:
            env_candidates.append(stage_ai_key_env)
        env_candidates.extend([defaults["key_env"], "AI_API_KEY"])
    else:
        env_candidates = [stage_ai_key_env, "AI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"]

    env_candidates = [name for name in env_candidates if name]

    for env_name in env_candidates:
        if env_name and os.environ.get(env_name):
            return os.environ.get(env_name, ""), env_name

    return "", env_candidates[0]


def _resolve_provider_config(stage: str | None = None) -> dict[str, str]:
    """从环境变量解析当前 provider 配置"""
    prefix = _stage_prefix(stage)
    provider = (
        os.environ.get(f"{prefix}AI_PROVIDER", "")
        or os.environ.get("AI_PROVIDER", "deepseek")
    ).lower()

    if provider in _PROVIDER_DEFAULTS:
        defaults = _PROVIDER_DEFAULTS[provider]
    else:
        # 自定义 provider：必须手动设置所有参数
        defaults = {"base_url": "", "model": "", "key_env": "AI_API_KEY"}

    api_key, api_key_env = _resolve_api_key(provider, defaults, stage=stage)

    return {
        "base_url": (
            os.environ.get(f"{prefix}AI_BASE_URL", "")
            or os.environ.get("AI_BASE_URL")
            or ""
        ).rstrip("/") or defaults["base_url"],
        "model": (
            os.environ.get(f"{prefix}AI_MODEL", "")
            or os.environ.get("AI_MODEL", "")
            or defaults["model"]
        ),
        "api_key": api_key,
        "api_key_env": api_key_env,
        "provider": provider,
    }


def build_llm_payload(prompt: str, stage: str | None = None) -> dict[str, object]:
    """构建 OpenAI 兼容格式的请求 payload"""
    config = _resolve_provider_config(stage=stage)
    return {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(os.environ.get("AI_TEMPERATURE", "0.2")),
    }


# Session 复用 — TCP 连接保持，减少每次 ~100ms 握手开销
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})
_metrics_lock = threading.Lock()


def _empty_token_usage() -> dict[str, int]:
    return {
        "prompt": 0,
        "completion": 0,
        "total": 0,
    }


def _default_llm_metrics(config: dict[str, str] | None = None) -> dict[str, object]:
    resolved = config or _resolve_provider_config()
    return {
        "provider": resolved.get("provider", ""),
        "model": resolved.get("model", ""),
        "calls": 0,
        "token_usage": _empty_token_usage(),
        "latency_seconds": 0.0,
        "stage_breakdown": {},
    }


_llm_metrics = _default_llm_metrics()


def reset_llm_metrics() -> None:
    global _llm_metrics
    with _metrics_lock:
        _llm_metrics = _default_llm_metrics()


def get_llm_metrics() -> dict[str, object]:
    with _metrics_lock:
        usage = _llm_metrics.get("token_usage", {})
        usage_dict = usage if isinstance(usage, dict) else {}
        return {
            "provider": str(_llm_metrics.get("provider", "")),
            "model": str(_llm_metrics.get("model", "")),
            "calls": int(_llm_metrics.get("calls", 0)),
            "token_usage": {
                "prompt": int(usage_dict.get("prompt", 0)),
                "completion": int(usage_dict.get("completion", 0)),
                "total": int(usage_dict.get("total", 0)),
            },
            "latency_seconds": round(float(_llm_metrics.get("latency_seconds", 0.0)), 2),
            "stage_breakdown": {
                str(stage_name): {
                    "provider": str(stage_metrics.get("provider", "")),
                    "model": str(stage_metrics.get("model", "")),
                    "calls": int(stage_metrics.get("calls", 0)),
                    "token_usage": {
                        "prompt": int((stage_metrics.get("token_usage", {}) or {}).get("prompt", 0)),
                        "completion": int((stage_metrics.get("token_usage", {}) or {}).get("completion", 0)),
                        "total": int((stage_metrics.get("token_usage", {}) or {}).get("total", 0)),
                    },
                    "latency_seconds": round(float(stage_metrics.get("latency_seconds", 0.0)), 2),
                }
                for stage_name, stage_metrics in (_llm_metrics.get("stage_breakdown", {}) or {}).items()
                if isinstance(stage_metrics, dict)
            },
        }


def _record_llm_metrics(
    config: dict[str, str],
    data: dict[str, object],
    elapsed_seconds: float,
    stage: str | None = None,
) -> None:
    usage = data.get("usage", {})
    usage_dict = usage if isinstance(usage, dict) else {}
    prompt_tokens = int(usage_dict.get("prompt_tokens", 0) or 0)
    completion_tokens = int(usage_dict.get("completion_tokens", 0) or 0)
    total_tokens = int(
        usage_dict.get("total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    )

    with _metrics_lock:
        current_provider = str(_llm_metrics.get("provider", ""))
        current_model = str(_llm_metrics.get("model", ""))
        next_provider = config.get("provider", "")
        next_model = config.get("model", "")

        if int(_llm_metrics.get("calls", 0)) == 0:
            _llm_metrics["provider"] = next_provider
            _llm_metrics["model"] = next_model
        elif current_provider != next_provider or current_model != next_model:
            _llm_metrics["provider"] = "mixed"
            _llm_metrics["model"] = "mixed"

        _llm_metrics["calls"] = int(_llm_metrics.get("calls", 0)) + 1
        current_usage = _llm_metrics.get("token_usage", {})
        current_usage_dict = current_usage if isinstance(current_usage, dict) else _empty_token_usage()
        _llm_metrics["token_usage"] = {
            "prompt": int(current_usage_dict.get("prompt", 0)) + prompt_tokens,
            "completion": int(current_usage_dict.get("completion", 0)) + completion_tokens,
            "total": int(current_usage_dict.get("total", 0)) + total_tokens,
        }
        _llm_metrics["latency_seconds"] = round(
            float(_llm_metrics.get("latency_seconds", 0.0)) + float(elapsed_seconds),
            2,
        )

        if stage:
            stage_breakdown = _llm_metrics.setdefault("stage_breakdown", {})
            current_stage_metrics = stage_breakdown.get(stage, {})
            current_stage_usage = current_stage_metrics.get("token_usage", {})
            current_stage_usage_dict = (
                current_stage_usage if isinstance(current_stage_usage, dict) else _empty_token_usage()
            )
            stage_breakdown[stage] = {
                "provider": next_provider,
                "model": next_model,
                "calls": int(current_stage_metrics.get("calls", 0)) + 1,
                "token_usage": {
                    "prompt": int(current_stage_usage_dict.get("prompt", 0)) + prompt_tokens,
                    "completion": int(current_stage_usage_dict.get("completion", 0)) + completion_tokens,
                    "total": int(current_stage_usage_dict.get("total", 0)) + total_tokens,
                },
                "latency_seconds": round(
                    float(current_stage_metrics.get("latency_seconds", 0.0)) + float(elapsed_seconds),
                    2,
                ),
            }


def is_llm_enabled() -> bool:
    if _resolve_provider_config().get("api_key"):
        return True

    for stage in ("analysis", "summary", "forecast", "prefilter", "discovery", "search"):
        if _resolve_provider_config(stage=stage).get("api_key"):
            return True

    return False


def call_llm(prompt: str, stage: str | None = None) -> str:
    """
    调用任意 OpenAI 兼容的 LLM API。

    支持的后端（通过 AI_PROVIDER 环境变量切换）：
      - deepseek (默认): DeepSeek Chat
      - openai: OpenAI GPT 系列
      - 自定义：设 AI_BASE_URL + AI_MODEL + 对应的 *_API_KEY

    重试策略：
      - 最多 3 次重试
      - 网络超时/连接错误: 指数退避 1s -> 2s -> 4s
      - HTTP 429 Rate Limit: 等 60s 后重试
      - 超时时间递增: 45s -> 55s -> 65s
    """
    config = _resolve_provider_config(stage=stage)
    api_key = config.get("api_key", "")
    base_url = config["base_url"]

    if not api_key:
        raise RuntimeError(
            f"API key not configured for provider '{config['provider']}'. "
            f"Set {config['api_key_env']} environment variable."
        )
    if not base_url:
        raise RuntimeError(
            f"Base URL not configured for provider '{config['provider']}'. "
            "Set AI_BASE_URL environment variable."
        )

    # 构建完整 URL（确保以 /chat/completions 结尾）
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"

    max_retries = 3

    for attempt in range(max_retries):
        try:
            started_at = time.perf_counter()
            base_timeout = 45 + attempt * 10  # 45s, 55s, 65s
            response = _session.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                json=build_llm_payload(prompt, stage=stage),
                timeout=base_timeout,
            )
            response.raise_for_status()
            data = response.json()
            _record_llm_metrics(config, data, time.perf_counter() - started_at, stage=stage)
            return data["choices"][0]["message"]["content"]

        except requests.exceptions.Timeout as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"LLM API timeout after {max_retries} attempts ({config['provider']})"
            ) from exc

        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code == 429 and attempt < max_retries - 1:
                time.sleep(60)
                continue
            raise

        except requests.exceptions.ConnectionError as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            raise RuntimeError(
                f"LLM API connection failed after {max_retries} attempts ({config['provider']})"
            ) from exc

    raise RuntimeError(f"LLM API failed after {max_retries} attempts")


# ── 向后兼容别名 ────────────────────────────────────

summarize_with_deepseek = call_llm
"""向后兼容：旧的 summarize_with_deepseek 名称指向新的通用 call_llm 函数"""
