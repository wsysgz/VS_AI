"""通用 LLM 客户端 — 支持 OpenAI 兼容接口（DeepSeek / OpenAI / LiteLLM Gateway / 本地部署等）

通过环境变量切换后端，无需改代码：
  AI_PROVIDER=deepseek  (默认)
  AI_PROVIDER=openai
  AI_PROVIDER=litellm_proxy
  AI_BASE_URL=https://api.deepseek.com
  AI_MODEL=deepseek-chat
  DEEPSEEK_API_KEY / OPENAI_API_KEY / LITELLM_MASTER_KEY
"""

from __future__ import annotations

import os
import threading
import time

import requests

from auto_report.integrations.langfuse_tracing import (
    finish_generation_trace,
    start_generation_trace,
)


# ── Provider 配置注册表 ──────────────────────────────

# 每个 provider 的默认配置
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "key_env": "DEEPSEEK_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "litellm_proxy": {
        "base_url": "http://127.0.0.1:4000",
        "model": "vs-ai-default",
        "key_env": "LITELLM_MASTER_KEY",
    },
}

_DEEPSEEK_STAGE_MODEL_DEFAULTS: dict[str, str] = {
    "analysis": "deepseek-v4-pro",
    "summary": "deepseek-v4-pro",
    "forecast": "deepseek-v4-pro",
    "prefilter": "deepseek-v4-flash",
    "discovery": "deepseek-v4-flash",
    "search": "deepseek-v4-flash",
}


class _StageGuardrailError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _stage_prefix(stage: str | None = None) -> str:
    normalized = str(stage or "").strip().upper()
    return f"{normalized}_" if normalized else ""


def _llm_forced_disabled() -> bool:
    return os.environ.get("AI_DISABLE_LLM", "").strip().lower() in {"1", "true", "yes", "on"}


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
    stage_provider = os.environ.get(f"{prefix}AI_PROVIDER", "").strip().lower()
    global_provider = os.environ.get("AI_PROVIDER", "deepseek").strip().lower()
    provider = (stage_provider or global_provider).lower()

    if provider in _PROVIDER_DEFAULTS:
        defaults = _PROVIDER_DEFAULTS[provider]
    else:
        # 自定义 provider：必须手动设置所有参数
        defaults = {"base_url": "", "model": "", "key_env": "AI_API_KEY"}

    api_key, api_key_env = _resolve_api_key(provider, defaults, stage=stage)
    use_global_fallback = not stage_provider or stage_provider == global_provider
    stage_base_url = os.environ.get(f"{prefix}AI_BASE_URL", "")
    stage_model = os.environ.get(f"{prefix}AI_MODEL", "")
    global_model = os.environ.get("AI_MODEL", "") if use_global_fallback else ""
    stage_name = str(stage or "").strip().lower()
    stage_default_model = _DEEPSEEK_STAGE_MODEL_DEFAULTS.get(stage_name, "") if provider == "deepseek" else ""
    if stage_model:
        resolved_model = stage_model
    elif stage_default_model and not global_model:
        resolved_model = stage_default_model
    else:
        resolved_model = global_model or defaults["model"]

    return {
        "base_url": (
            stage_base_url
            or (os.environ.get("AI_BASE_URL") if use_global_fallback else "")
            or ""
        ).rstrip("/") or defaults["base_url"],
        "model": resolved_model,
        "api_key": api_key,
        "api_key_env": api_key_env,
        "provider": provider,
    }


def _resolve_backup_provider_config(stage: str | None = None) -> dict[str, str] | None:
    prefix = _stage_prefix(stage)
    stage_provider = os.environ.get(f"{prefix}BACKUP_AI_PROVIDER", "").strip().lower()
    global_provider = os.environ.get("BACKUP_AI_PROVIDER", "").strip().lower()
    provider = (stage_provider or global_provider).lower()

    if not provider:
        return None

    if provider in _PROVIDER_DEFAULTS:
        defaults = _PROVIDER_DEFAULTS[provider]
    else:
        defaults = {"base_url": "", "model": "", "key_env": "AI_API_KEY"}

    use_global_fallback = not stage_provider or stage_provider == global_provider
    stage_base_url = os.environ.get(f"{prefix}BACKUP_AI_BASE_URL", "")
    stage_model = os.environ.get(f"{prefix}BACKUP_AI_MODEL", "")
    stage_backup_key_env = f"{prefix}BACKUP_AI_API_KEY" if prefix else ""

    env_candidates = [stage_backup_key_env, "BACKUP_AI_API_KEY"]
    if provider in _PROVIDER_DEFAULTS:
        if prefix:
            env_candidates.append(f"{prefix}{defaults['key_env']}")
        env_candidates.extend([defaults["key_env"], "AI_API_KEY"])
    else:
        env_candidates.extend([f"{prefix}AI_API_KEY" if prefix else "", "AI_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"])

    env_candidates = [name for name in env_candidates if name]
    api_key = ""
    api_key_env = env_candidates[0] if env_candidates else "BACKUP_AI_API_KEY"
    for env_name in env_candidates:
        if env_name and os.environ.get(env_name):
            api_key = os.environ.get(env_name, "")
            api_key_env = env_name
            break

    return {
        "base_url": (
            stage_base_url
            or (os.environ.get("BACKUP_AI_BASE_URL") if use_global_fallback else "")
            or ""
        ).rstrip("/") or defaults["base_url"],
        "model": (
            stage_model
            or (os.environ.get("BACKUP_AI_MODEL", "") if use_global_fallback else "")
            or defaults["model"]
        ),
        "api_key": api_key,
        "api_key_env": api_key_env,
        "provider": provider,
    }


def _parse_float_limit(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int_limit(value: str) -> int | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _resolve_stage_budget(stage: str | None = None) -> dict[str, float | int | None]:
    prefix = _stage_prefix(stage)
    return {
        "max_latency_seconds": _parse_float_limit(
            os.environ.get(f"{prefix}AI_MAX_LATENCY_SECONDS", "") or os.environ.get("AI_MAX_STAGE_LATENCY_SECONDS", "")
        ),
        "max_total_tokens": _parse_int_limit(
            os.environ.get(f"{prefix}AI_MAX_TOTAL_TOKENS", "") or os.environ.get("AI_MAX_STAGE_TOTAL_TOKENS", "")
        ),
    }


def build_llm_payload(prompt: str, stage: str | None = None, config: dict[str, str] | None = None) -> dict[str, object]:
    """构建 OpenAI 兼容格式的请求 payload"""
    resolved_config = config or _resolve_provider_config(stage=stage)
    return {
        "model": resolved_config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": float(os.environ.get("AI_TEMPERATURE", "0.2")),
    }


# Session 复用 — TCP 连接保持，减少每次 ~100ms 握手开销
_session = requests.Session()
_session.headers.update({"Content-Type": "application/json"})
_metrics_lock = threading.RLock()


def _empty_token_usage() -> dict[str, int]:
    return {
        "prompt": 0,
        "completion": 0,
        "total": 0,
    }


def _default_llm_metrics(config: dict[str, str] | None = None) -> dict[str, object]:
    if _llm_forced_disabled():
        return {
            "provider": "disabled",
            "model": "",
            "calls": 0,
            "token_usage": _empty_token_usage(),
            "latency_seconds": 0.0,
            "backup_stages": [],
            "guardrail_stages": [],
            "stage_breakdown": {},
        }
    resolved = config or _resolve_provider_config()
    return {
        "provider": resolved.get("provider", ""),
        "model": resolved.get("model", ""),
        "calls": 0,
        "token_usage": _empty_token_usage(),
        "latency_seconds": 0.0,
        "backup_stages": [],
        "guardrail_stages": [],
        "stage_breakdown": {},
    }


def _default_stage_metrics(primary_config: dict[str, str], budget: dict[str, float | int | None]) -> dict[str, object]:
    return {
        "provider": primary_config.get("provider", ""),
        "model": primary_config.get("model", ""),
        "calls": 0,
        "token_usage": _empty_token_usage(),
        "latency_seconds": 0.0,
        "attempts": 0,
        "backup_used": False,
        "guardrail_triggered": False,
        "guardrail_reason": "",
        "primary_provider": primary_config.get("provider", ""),
        "primary_model": primary_config.get("model", ""),
        "final_provider": primary_config.get("provider", ""),
        "final_model": primary_config.get("model", ""),
        "budget": {
            "max_latency_seconds": budget.get("max_latency_seconds"),
            "max_total_tokens": budget.get("max_total_tokens"),
        },
    }


def _ensure_stage_metrics(stage: str, primary_config: dict[str, str], budget: dict[str, float | int | None]) -> dict[str, object]:
    with _metrics_lock:
        stage_breakdown = _llm_metrics.setdefault("stage_breakdown", {})
        stage_metrics = stage_breakdown.get(stage)
        if not isinstance(stage_metrics, dict):
            stage_metrics = _default_stage_metrics(primary_config, budget)
            stage_breakdown[stage] = stage_metrics
        else:
            stage_metrics["primary_provider"] = primary_config.get("provider", "")
            stage_metrics["primary_model"] = primary_config.get("model", "")
            stage_metrics["budget"] = {
                "max_latency_seconds": budget.get("max_latency_seconds"),
                "max_total_tokens": budget.get("max_total_tokens"),
            }
        return stage_metrics


def _register_stage_attempt(
    stage: str | None,
    primary_config: dict[str, str],
    budget: dict[str, float | int | None],
    active_config: dict[str, str],
    *,
    backup_used: bool,
) -> None:
    if not stage:
        return
    with _metrics_lock:
        stage_metrics = _ensure_stage_metrics(stage, primary_config, budget)
        stage_metrics["attempts"] = int(stage_metrics.get("attempts", 0)) + 1
        if backup_used:
            stage_metrics["backup_used"] = True
        stage_metrics["final_provider"] = active_config.get("provider", "")
        stage_metrics["final_model"] = active_config.get("model", "")


def _mark_stage_guardrail(stage: str | None, reason: str) -> None:
    if not stage:
        return
    with _metrics_lock:
        stage_breakdown = _llm_metrics.setdefault("stage_breakdown", {})
        stage_metrics = stage_breakdown.get(stage)
        if not isinstance(stage_metrics, dict):
            return
        stage_metrics["guardrail_triggered"] = True
        stage_metrics["guardrail_reason"] = reason


_llm_metrics = _default_llm_metrics()


def reset_llm_metrics() -> None:
    global _llm_metrics
    with _metrics_lock:
        _llm_metrics = _default_llm_metrics()


def get_llm_metrics() -> dict[str, object]:
    with _metrics_lock:
        usage = _llm_metrics.get("token_usage", {})
        usage_dict = usage if isinstance(usage, dict) else {}
        stage_breakdown_view: dict[str, object] = {}
        backup_stages: list[str] = []
        guardrail_stages: list[str] = []
        for stage_name, stage_metrics in (_llm_metrics.get("stage_breakdown", {}) or {}).items():
            if not isinstance(stage_metrics, dict):
                continue
            if bool(stage_metrics.get("backup_used", False)):
                backup_stages.append(str(stage_name))
            if bool(stage_metrics.get("guardrail_triggered", False)):
                guardrail_stages.append(str(stage_name))
            stage_breakdown_view[str(stage_name)] = {
                "provider": str(stage_metrics.get("provider", "")),
                "model": str(stage_metrics.get("model", "")),
                "calls": int(stage_metrics.get("calls", 0)),
                "token_usage": {
                    "prompt": int((stage_metrics.get("token_usage", {}) or {}).get("prompt", 0)),
                    "completion": int((stage_metrics.get("token_usage", {}) or {}).get("completion", 0)),
                    "total": int((stage_metrics.get("token_usage", {}) or {}).get("total", 0)),
                },
                "latency_seconds": round(float(stage_metrics.get("latency_seconds", 0.0)), 2),
                "attempts": int(stage_metrics.get("attempts", 0)),
                "backup_used": bool(stage_metrics.get("backup_used", False)),
                "guardrail_triggered": bool(stage_metrics.get("guardrail_triggered", False)),
                "guardrail_reason": str(stage_metrics.get("guardrail_reason", "")),
                "primary_provider": str(stage_metrics.get("primary_provider", "")),
                "primary_model": str(stage_metrics.get("primary_model", "")),
                "final_provider": str(stage_metrics.get("final_provider", "")),
                "final_model": str(stage_metrics.get("final_model", "")),
                "budget": {
                    "max_latency_seconds": (stage_metrics.get("budget", {}) or {}).get("max_latency_seconds"),
                    "max_total_tokens": (stage_metrics.get("budget", {}) or {}).get("max_total_tokens"),
                },
            }
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
            "backup_stages": backup_stages,
            "guardrail_stages": guardrail_stages,
            "stage_breakdown": stage_breakdown_view,
        }


def _record_llm_metrics(
    config: dict[str, str],
    data: dict[str, object],
    elapsed_seconds: float,
    stage: str | None = None,
    primary_config: dict[str, str] | None = None,
    budget: dict[str, float | int | None] | None = None,
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
        else:
            if current_provider != next_provider:
                _llm_metrics["provider"] = "mixed"
            if current_model != next_model:
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
            current_stage_metrics = _ensure_stage_metrics(stage, primary_config or config, budget or {})
            current_stage_usage = current_stage_metrics.get("token_usage", {})
            current_stage_usage_dict = (
                current_stage_usage if isinstance(current_stage_usage, dict) else _empty_token_usage()
            )
            _llm_metrics.setdefault("stage_breakdown", {})[stage] = {
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
                "attempts": int(current_stage_metrics.get("attempts", 0)),
                "backup_used": bool(current_stage_metrics.get("backup_used", False)),
                "guardrail_triggered": bool(current_stage_metrics.get("guardrail_triggered", False)),
                "guardrail_reason": str(current_stage_metrics.get("guardrail_reason", "")),
                "primary_provider": str(current_stage_metrics.get("primary_provider", primary_config.get("provider", "") if primary_config else "")),
                "primary_model": str(current_stage_metrics.get("primary_model", primary_config.get("model", "") if primary_config else "")),
                "final_provider": next_provider,
                "final_model": next_model,
                "budget": {
                    "max_latency_seconds": ((current_stage_metrics.get("budget", {}) or {}).get("max_latency_seconds")),
                    "max_total_tokens": ((current_stage_metrics.get("budget", {}) or {}).get("max_total_tokens")),
                },
            }


def _guardrail_reason(
    budget: dict[str, float | int | None],
    elapsed_seconds: float,
    total_tokens: int,
) -> str | None:
    max_latency = budget.get("max_latency_seconds")
    if isinstance(max_latency, (int, float)) and float(elapsed_seconds) > float(max_latency):
        return "latency_exceeded"

    max_tokens = budget.get("max_total_tokens")
    if isinstance(max_tokens, int) and int(total_tokens) > int(max_tokens):
        return "token_exceeded"

    return None


def _call_provider_with_retries(
    prompt: str,
    *,
    stage: str | None,
    config: dict[str, str],
    primary_config: dict[str, str],
    budget: dict[str, float | int | None],
    backup_used: bool,
    outer_attempt: int,
) -> str:
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

    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"

    max_retries = 3
    payload = build_llm_payload(prompt, stage=stage, config=config)
    generation_trace = start_generation_trace(
        stage=stage,
        provider=str(config.get("provider", "")),
        model=str(config.get("model", "")),
        input_payload=payload,
        metadata={
            "api_key_env": str(config.get("api_key_env", "")),
            "base_url": endpoint,
            "outer_attempt": outer_attempt,
            "backup_used": backup_used,
        },
    )

    for attempt in range(max_retries):
        try:
            started_at = time.perf_counter()
            base_timeout = 45 + attempt * 10
            response = _session.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                json=payload,
                timeout=base_timeout,
            )
            response.raise_for_status()
            data = response.json()
            elapsed_seconds = time.perf_counter() - started_at
            _record_llm_metrics(
                config,
                data,
                elapsed_seconds,
                stage=stage,
                primary_config=primary_config,
                budget=budget,
            )

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            usage_dict = usage if isinstance(usage, dict) else {}
            total_tokens = int(usage_dict.get("total_tokens", 0) or 0)
            guardrail = _guardrail_reason(budget, elapsed_seconds, total_tokens)
            if guardrail:
                _mark_stage_guardrail(stage, guardrail)
                finish_generation_trace(
                    generation_trace,
                    output_text=content,
                    usage_details={
                        "prompt_tokens": int(usage_dict.get("prompt_tokens", 0) or 0),
                        "completion_tokens": int(usage_dict.get("completion_tokens", 0) or 0),
                        "total_tokens": total_tokens,
                    },
                    metadata={
                        "stage": stage or "default",
                        "provider": str(config.get("provider", "")),
                        "model": str(config.get("model", "")),
                        "http_status": int(getattr(response, "status_code", 200) or 200),
                        "attempt": attempt + 1,
                        "outer_attempt": outer_attempt,
                        "backup_used": backup_used,
                        "status": "guardrail_triggered",
                        "guardrail_reason": guardrail,
                    },
                    error=guardrail,
                )
                raise _StageGuardrailError(guardrail)

            finish_generation_trace(
                generation_trace,
                output_text=content,
                usage_details={
                    "prompt_tokens": int(usage_dict.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(usage_dict.get("completion_tokens", 0) or 0),
                    "total_tokens": total_tokens,
                },
                metadata={
                    "stage": stage or "default",
                    "provider": str(config.get("provider", "")),
                    "model": str(config.get("model", "")),
                    "http_status": int(getattr(response, "status_code", 200) or 200),
                    "attempt": attempt + 1,
                    "outer_attempt": outer_attempt,
                    "backup_used": backup_used,
                    "status": "ok",
                },
            )
            return content

        except requests.exceptions.Timeout as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            finish_generation_trace(
                generation_trace,
                metadata={
                    "stage": stage or "default",
                    "provider": str(config.get("provider", "")),
                    "model": str(config.get("model", "")),
                    "attempt": attempt + 1,
                    "outer_attempt": outer_attempt,
                    "backup_used": backup_used,
                    "status": "timeout",
                },
                error=str(exc),
            )
            raise RuntimeError(
                f"LLM API timeout after {max_retries} attempts ({config['provider']})"
            ) from exc

        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            if status_code == 429 and attempt < max_retries - 1:
                time.sleep(60)
                continue
            finish_generation_trace(
                generation_trace,
                metadata={
                    "stage": stage or "default",
                    "provider": str(config.get("provider", "")),
                    "model": str(config.get("model", "")),
                    "attempt": attempt + 1,
                    "outer_attempt": outer_attempt,
                    "backup_used": backup_used,
                    "status": "http_error",
                    "http_status": status_code,
                },
                error=str(exc),
            )
            raise

        except requests.exceptions.ConnectionError as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            finish_generation_trace(
                generation_trace,
                metadata={
                    "stage": stage or "default",
                    "provider": str(config.get("provider", "")),
                    "model": str(config.get("model", "")),
                    "attempt": attempt + 1,
                    "outer_attempt": outer_attempt,
                    "backup_used": backup_used,
                    "status": "connection_error",
                },
                error=str(exc),
            )
            raise RuntimeError(
                f"LLM API connection failed after {max_retries} attempts ({config['provider']})"
            ) from exc


def is_llm_enabled() -> bool:
    if _llm_forced_disabled():
        return False
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
      - litellm_proxy: LiteLLM Gateway / Proxy
      - 自定义：设 AI_BASE_URL + AI_MODEL + 对应的 *_API_KEY

    重试策略：
      - 最多 3 次重试
      - 网络超时/连接错误: 指数退避 1s -> 2s -> 4s
      - HTTP 429 Rate Limit: 等 60s 后重试
      - 超时时间递增: 45s -> 55s -> 65s
    """
    if _llm_forced_disabled():
        raise RuntimeError("LLM calls are disabled by AI_DISABLE_LLM")

    primary_config = _resolve_provider_config(stage=stage)
    backup_config = _resolve_backup_provider_config(stage=stage)
    budget = _resolve_stage_budget(stage=stage)

    if stage:
        _ensure_stage_metrics(stage, primary_config, budget)

    configs: list[tuple[dict[str, str], bool]] = [(primary_config, False)]
    if backup_config and backup_config != primary_config:
        configs.append((backup_config, True))

    last_error: Exception | None = None
    for outer_attempt, (active_config, backup_used) in enumerate(configs, start=1):
        _register_stage_attempt(stage, primary_config, budget, active_config, backup_used=backup_used)
        try:
            return _call_provider_with_retries(
                prompt,
                stage=stage,
                config=active_config,
                primary_config=primary_config,
                budget=budget,
                backup_used=backup_used,
                outer_attempt=outer_attempt,
            )
        except _StageGuardrailError as exc:
            last_error = RuntimeError(
                f"LLM guardrail exceeded for stage '{stage or 'default'}': {exc.reason}"
            )
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise RuntimeError("LLM API failed without a captured error")


# ── 向后兼容别名 ────────────────────────────────────

summarize_with_deepseek = call_llm
"""向后兼容：旧的 summarize_with_deepseek 名称指向新的通用 call_llm 函数"""
