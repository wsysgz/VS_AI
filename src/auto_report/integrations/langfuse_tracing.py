from __future__ import annotations

import os
import threading
from typing import Any, Mapping


_client_lock = threading.Lock()
_langfuse_client: Any | None = None
_langfuse_signature: tuple[str, str, str, str] | None = None
_active_trace_state: dict[str, Any] | None = None


def reset_langfuse_state() -> None:
    global _langfuse_client, _langfuse_signature, _active_trace_state
    with _client_lock:
        _langfuse_client = None
        _langfuse_signature = None
        _active_trace_state = None


def _resolve_env(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return env if env is not None else os.environ


def _env_flag(name: str, env: Mapping[str, str]) -> bool:
    return str(env.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def is_langfuse_enabled(env: Mapping[str, str] | None = None) -> bool:
    resolved = _resolve_env(env)
    return (
        _env_flag("LANGFUSE_ENABLED", resolved)
        and bool(str(resolved.get("LANGFUSE_PUBLIC_KEY", "")).strip())
        and bool(str(resolved.get("LANGFUSE_SECRET_KEY", "")).strip())
    )


def is_langfuse_capture_content_enabled(env: Mapping[str, str] | None = None) -> bool:
    return _env_flag("LANGFUSE_CAPTURE_CONTENT", _resolve_env(env))


def sanitize_llm_content(value: Any, capture_content: bool) -> Any | None:
    if not capture_content:
        return None
    return value


def _load_langfuse_class():
    try:
        from langfuse import Langfuse  # type: ignore
    except Exception:
        return None
    return Langfuse


def get_langfuse_client(env: Mapping[str, str] | None = None) -> Any | None:
    global _langfuse_client, _langfuse_signature

    resolved = _resolve_env(env)
    if not is_langfuse_enabled(resolved):
        return None

    signature = (
        str(resolved.get("LANGFUSE_PUBLIC_KEY", "")).strip(),
        str(resolved.get("LANGFUSE_SECRET_KEY", "")).strip(),
        str(resolved.get("LANGFUSE_BASE_URL", "")).strip(),
        str(resolved.get("LANGFUSE_ENV", "")).strip(),
    )

    with _client_lock:
        if _langfuse_client is not None and _langfuse_signature == signature:
            return _langfuse_client

        Langfuse = _load_langfuse_class()
        if Langfuse is None:
            return None

        kwargs: dict[str, Any] = {
            "public_key": signature[0],
            "secret_key": signature[1],
        }
        if signature[2]:
            kwargs["base_url"] = signature[2]
        if signature[3]:
            kwargs["environment"] = signature[3]

        try:
            _langfuse_client = Langfuse(**kwargs)
        except Exception:
            return None

        _langfuse_signature = signature
        return _langfuse_client


def get_active_trace_state() -> dict[str, Any] | None:
    with _client_lock:
        return _active_trace_state


def clear_active_trace_state() -> None:
    global _active_trace_state
    with _client_lock:
        _active_trace_state = None


def build_tracing_status(trace_state: dict[str, Any] | None) -> dict[str, object]:
    if not trace_state or not trace_state.get("enabled"):
        return {"enabled": False}

    status: dict[str, object] = {
        "enabled": True,
        "trace_id": str(trace_state.get("trace_id", "")),
    }
    trace_url = str(trace_state.get("trace_url", "")).strip()
    if trace_url:
        status["trace_url"] = trace_url
    return status


def start_run_trace(
    env: Mapping[str, str] | None,
    *,
    name: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    global _active_trace_state

    resolved = _resolve_env(env)
    client = get_langfuse_client(resolved)
    if client is None:
        clear_active_trace_state()
        return {"enabled": False}

    try:
        root = client.start_observation(
            name=name,
            as_type="span",
            metadata=metadata,
        )
    except Exception as exc:
        clear_active_trace_state()
        return {
            "enabled": False,
            "error": str(exc),
        }

    trace_state: dict[str, Any] = {
        "enabled": True,
        "client": client,
        "env": dict(resolved),
        "root": root,
        "trace_id": getattr(root, "trace_id", ""),
        "root_span_id": getattr(root, "id", ""),
        "stage_spans": {},
        "capture_content": is_langfuse_capture_content_enabled(resolved),
    }
    try:
        trace_state["trace_url"] = client.get_trace_url(trace_state["trace_id"])
    except Exception:
        trace_state["trace_url"] = ""

    with _client_lock:
        _active_trace_state = trace_state
    return trace_state


def _parent_span_id(trace_state: dict[str, Any], parent_name: str | None) -> str:
    if parent_name:
        parent = trace_state.get("stage_spans", {}).get(parent_name)
        if parent is not None:
            return str(getattr(parent, "id", "") or "")
    return str(trace_state.get("root_span_id", "") or "")


def start_stage_span(
    name: str,
    *,
    parent_name: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trace_state = get_active_trace_state()
    if not trace_state or not trace_state.get("enabled"):
        return None

    try:
        span = trace_state["client"].start_observation(
            trace_context={
                "trace_id": trace_state["trace_id"],
                "parent_span_id": _parent_span_id(trace_state, parent_name),
            },
            name=name,
            as_type="span",
            metadata=metadata,
        )
        trace_state.setdefault("stage_spans", {})[name] = span
        return {
            "observation_id": getattr(span, "id", ""),
            "trace_id": getattr(span, "trace_id", ""),
        }
    except Exception:
        return None


def finish_stage_span(
    name: str,
    *,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    trace_state = get_active_trace_state()
    if not trace_state or not trace_state.get("enabled"):
        return

    span = trace_state.get("stage_spans", {}).get(name)
    if span is None:
        return

    update_kwargs: dict[str, Any] = {}
    if metadata is not None:
        update_kwargs["metadata"] = metadata
    if error:
        update_kwargs["level"] = "ERROR"
        update_kwargs["status_message"] = error
    if update_kwargs:
        span.update(**update_kwargs)
    span.end()


def start_generation_trace(
    *,
    stage: str | None,
    provider: str,
    model: str,
    input_payload: Any | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    trace_state = get_active_trace_state()
    if not trace_state or not trace_state.get("enabled"):
        return None

    capture_content = bool(trace_state.get("capture_content", False))
    generation_metadata = {
        "stage": stage or "default",
        "provider": provider,
        "model": model,
        **(metadata or {}),
    }

    try:
        observation = trace_state["client"].start_observation(
            trace_context={
                "trace_id": trace_state["trace_id"],
                "parent_span_id": _parent_span_id(trace_state, stage),
            },
            name=f"llm:{stage or 'default'}",
            as_type="generation",
            model=model,
            input=sanitize_llm_content(input_payload, capture_content),
            metadata=generation_metadata,
        )
        return {
            "observation": observation,
            "observation_id": getattr(observation, "id", ""),
            "trace_id": getattr(observation, "trace_id", ""),
            "capture_content": capture_content,
        }
    except Exception:
        return None


def finish_generation_trace(
    trace_observation: dict[str, Any] | None,
    *,
    output_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    usage_details: dict[str, int] | None = None,
    error: str | None = None,
) -> None:
    if not trace_observation:
        return

    observation = trace_observation.get("observation")
    if observation is None:
        return

    update_kwargs: dict[str, Any] = {}
    if output_text is not None:
        update_kwargs["output"] = sanitize_llm_content(
            output_text,
            bool(trace_observation.get("capture_content", False)),
        )
    if metadata is not None:
        update_kwargs["metadata"] = metadata
    if usage_details is not None:
        update_kwargs["usage_details"] = usage_details
    if error:
        update_kwargs["level"] = "ERROR"
        update_kwargs["status_message"] = error
    if update_kwargs:
        observation.update(**update_kwargs)
    observation.end()


def complete_run_trace(
    trace_state: dict[str, Any] | None,
    *,
    metadata: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    if not trace_state or not trace_state.get("enabled"):
        clear_active_trace_state()
        return

    root = trace_state.get("root")
    if root is None:
        clear_active_trace_state()
        return

    update_kwargs: dict[str, Any] = {}
    if metadata is not None:
        update_kwargs["metadata"] = metadata
    if error:
        update_kwargs["level"] = "ERROR"
        update_kwargs["status_message"] = error
    if update_kwargs:
        root.update(**update_kwargs)
    root.end()
    clear_active_trace_state()


def flush_langfuse(env: Mapping[str, str] | None = None) -> None:
    client = get_langfuse_client(env)
    if client is None:
        return
    try:
        client.flush()
    except Exception:
        return
