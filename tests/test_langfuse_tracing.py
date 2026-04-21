import auto_report.integrations.langfuse_tracing as tracing
from auto_report.integrations.langfuse_tracing import (
    build_tracing_status,
    complete_run_trace,
    finish_stage_span,
    finish_generation_trace,
    is_langfuse_capture_content_enabled,
    is_langfuse_enabled,
    reset_langfuse_state,
    sanitize_llm_content,
    start_generation_trace,
    start_run_trace,
    start_stage_span,
)


def setup_function():
    reset_langfuse_state()


def test_langfuse_is_enabled_requires_flag_and_keys():
    assert is_langfuse_enabled({}) is False
    assert is_langfuse_enabled(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        }
    ) is True


def test_langfuse_capture_content_is_disabled_by_default():
    assert is_langfuse_capture_content_enabled({}) is False
    assert is_langfuse_capture_content_enabled({"LANGFUSE_CAPTURE_CONTENT": "true"}) is True


def test_sanitize_llm_content_returns_none_when_capture_disabled():
    assert sanitize_llm_content("secret prompt", capture_content=False) is None
    assert sanitize_llm_content("secret prompt", capture_content=True) == "secret prompt"


def test_build_tracing_status_defaults_disabled():
    assert build_tracing_status(None) == {"enabled": False}


def test_build_tracing_status_includes_trace_url_when_present():
    status = build_tracing_status(
        {
            "enabled": True,
            "trace_id": "trace-123",
            "trace_url": "https://langfuse.example/trace/trace-123",
        }
    )

    assert status["enabled"] is True
    assert status["trace_id"] == "trace-123"
    assert status["trace_url"] == "https://langfuse.example/trace/trace-123"


class _FakeObservation:
    def __init__(
        self,
        name: str,
        trace_id: str,
        obs_id: str,
        trace_context=None,
        raise_on_update: bool = False,
        raise_on_end: bool = False,
        **kwargs,
    ):
        self.name = name
        self.trace_id = trace_id
        self.id = obs_id
        self.trace_context = trace_context or {}
        self.raise_on_update = raise_on_update
        self.raise_on_end = raise_on_end
        self.kwargs = kwargs
        self.updates = []
        self.ended = False

    def update(self, **kwargs):
        if self.raise_on_update:
            raise RuntimeError(f"update failed for {self.name}")
        self.updates.append(kwargs)

    def end(self):
        if self.raise_on_end:
            raise RuntimeError(f"end failed for {self.name}")
        self.ended = True


class _FakeClient:
    def __init__(self):
        self.observations = []
        self.counter = 0

    def start_observation(self, **kwargs):
        self.counter += 1
        trace_context = kwargs.get("trace_context") or {}
        trace_id = trace_context.get("trace_id") or f"trace-{self.counter}"
        payload = dict(kwargs)
        obs = _FakeObservation(
            name=payload.pop("name", ""),
            trace_id=trace_id,
            obs_id=f"obs-{self.counter}",
            **payload,
        )
        self.observations.append(obs)
        return obs

    def get_trace_url(self, trace_id: str):
        return f"https://langfuse.example/trace/{trace_id}"

    def flush(self):
        return None


class _FakeClientKeywordTraceUrl(_FakeClient):
    def get_trace_url(self, *, trace_id: str | None = None):
        return f"https://langfuse.example/trace/{trace_id}"


def test_start_run_trace_reads_trace_url_with_keyword_only_sdk(monkeypatch):
    fake_client = _FakeClientKeywordTraceUrl()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
        name="vs-ai-run-once",
        metadata={"publication_mode": "reviewed"},
    )

    assert trace_state["enabled"] is True
    assert trace_state["trace_id"] == "trace-1"
    assert trace_state["trace_url"] == "https://langfuse.example/trace/trace-1"


def test_start_generation_trace_can_parent_under_named_span(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
        name="vs-ai-evaluate-prompts",
        metadata={"dataset_path": "dataset.json"},
    )

    assert trace_state["enabled"] is True
    start_stage_span("prompt-eval-case:summary-case", metadata={"case_id": "summary-case"})

    observation = start_generation_trace(
        stage="prompt_eval",
        parent_name="prompt-eval-case:summary-case",
        provider="offline_eval",
        model="offline-dataset",
        input_payload={"content": {"one_line_core": "secret"}},
        metadata={"case_id": "summary-case", "prompt_id": "summary-v2"},
    )

    assert observation is not None
    assert fake_client.observations[-1].trace_context["parent_span_id"] == "obs-2"
    assert fake_client.observations[-1].name == "llm:prompt_eval"


def test_finish_stage_span_swallows_langfuse_update_and_end_errors(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        },
        name="vs-ai-run-once",
    )

    start_stage_span("analysis")
    trace_state = tracing.get_active_trace_state()
    assert trace_state is not None

    trace_state["stage_spans"]["analysis"] = _FakeObservation(
        "analysis",
        "trace-1",
        "obs-stage-update",
        raise_on_update=True,
    )
    finish_stage_span("analysis", metadata={"status": "ok"})

    trace_state["stage_spans"]["analysis"] = _FakeObservation(
        "analysis",
        "trace-1",
        "obs-stage-end",
        raise_on_end=True,
    )
    finish_stage_span("analysis")


def test_finish_generation_trace_swallows_langfuse_update_and_end_errors(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        },
        name="vs-ai-run-once",
    )

    finish_generation_trace(
        {"observation": _FakeObservation("llm:analysis", "trace-1", "obs-gen-update", raise_on_update=True)},
        output_text="secret answer",
    )

    finish_generation_trace(
        {"observation": _FakeObservation("llm:analysis", "trace-1", "obs-gen-end", raise_on_end=True)},
    )


def test_complete_run_trace_swallows_langfuse_update_and_end_errors(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        },
        name="vs-ai-run-once",
    )

    trace_state["root"] = _FakeObservation(
        "vs-ai-run-once",
        "trace-1",
        "obs-root-update",
        raise_on_update=True,
    )
    complete_run_trace(trace_state, metadata={"status": "ok"})

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
        },
        name="vs-ai-run-once",
    )
    trace_state["root"] = _FakeObservation(
        "vs-ai-run-once",
        "trace-2",
        "obs-root-end",
        raise_on_end=True,
    )
    complete_run_trace(trace_state)


def test_start_run_trace_and_generation_use_metadata_first(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(tracing, "get_langfuse_client", lambda env=None: fake_client)

    trace_state = start_run_trace(
        {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test",
            "LANGFUSE_SECRET_KEY": "sk-lf-test",
            "LANGFUSE_CAPTURE_CONTENT": "false",
        },
        name="vs-ai-run-once",
        metadata={"publication_mode": "reviewed"},
    )

    assert trace_state["enabled"] is True
    assert trace_state["trace_id"] == "trace-1"

    start_stage_span("analysis", parent_name=None, metadata={"candidate_count": 2})
    generation = start_generation_trace(
        stage="analysis",
        provider="litellm_proxy",
        model="vs-ai-analysis",
        input_payload={"messages": [{"role": "user", "content": "secret prompt"}]},
        metadata={"base_url": "http://127.0.0.1:4000/chat/completions"},
    )

    finish_generation_trace(
        generation,
        output_text="secret answer",
        metadata={"stage": "analysis", "status": "ok"},
        usage_details={"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13},
    )
    complete_run_trace(trace_state, metadata={"risk_level": "low"})

    assert fake_client.observations[0].name == "vs-ai-run-once"
    assert fake_client.observations[1].trace_context["parent_span_id"] == "obs-1"
    assert fake_client.observations[2].trace_context["parent_span_id"] == "obs-2"
    assert fake_client.observations[2].kwargs["input"] is None
    assert fake_client.observations[2].kwargs["metadata"]["provider"] == "litellm_proxy"
    assert fake_client.observations[2].updates[-1]["output"] is None
    assert fake_client.observations[2].updates[-1]["usage_details"]["total_tokens"] == 13
