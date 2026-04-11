# External Enrichment Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add run-scoped external enrichment metrics, a single-run circuit breaker, and private dashboard visibility without changing public report payloads.

**Architecture:** Extend the existing intelligence layer to compute enrichment runtime diagnostics while it already decides which high-value topics receive external fetches. Persist the diagnostics into `run-status.json`, then render them in the private ops dashboard. Keep all observability private and reuse the existing run-status surface.

**Tech Stack:** Python 3.14, pytest, existing `auto_report` pipeline modules, private ops dashboard HTML renderer.

---

### Task 1: Add Failing Intelligence Tests For Enrichment Metrics

**Files:**
- Modify: `tests/test_intelligence.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_apply_intelligence_layer_tracks_external_enrichment_runtime_metrics(tmp_path: Path):
    attempts: list[str] = []

    def fake_external_fetcher(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        attempts.append(str(signal["title"]))
        if signal["title"] == "Topic A":
            return [{
                "source_id": "arxiv-search",
                "source_type": "paper",
                "title": "Support for Topic A",
                "url": "https://example.com/a-paper",
                "summary": "paper support",
                "evidence_scope": "external",
            }]
        return []

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {"title": "Topic A", "url": "https://example.com/a", "summary": "A", "primary_domain": "ai-llm-agent", "score": 3.6, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
            {"title": "Topic B", "url": "https://example.com/b", "summary": "B", "primary_domain": "ai-llm-agent", "score": 3.5, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
            {"title": "Topic C", "url": "https://example.com/c", "summary": "C", "primary_domain": "ai-llm-agent", "score": 2.0, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
        ],
        analyses=[
            {"title": "Topic A", "url": "https://example.com/a", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic B", "url": "https://example.com/b", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic C", "url": "https://example.com/c", "primary_domain": "ai-llm-agent", "confidence": "medium"},
        ],
        diagnostics=[],
        generated_at="2026-04-12T07:00:00+08:00",
        external_enrichment_fetcher=fake_external_fetcher,
        external_enrichment_max_signals=2,
    )

    metrics = result["external_enrichment"]
    assert attempts == ["Topic A", "Topic B"]
    assert metrics["enabled"] is True
    assert metrics["attempted"] == 2
    assert metrics["succeeded"] == 1
    assert metrics["failed"] == 1
    assert metrics["skipped"] == 1
    assert metrics["budget_used"] == 2
    assert metrics["success_rate"] == 0.5
    assert "below-threshold: Topic C" in metrics["reasons"]
    assert "empty-result: Topic B" in metrics["reasons"]

def test_apply_intelligence_layer_opens_circuit_after_two_consecutive_failures(tmp_path: Path):
    attempts: list[str] = []

    def always_fail(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        attempts.append(str(signal["title"]))
        return []

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {"title": "Topic A", "url": "https://example.com/a", "summary": "A", "primary_domain": "ai-llm-agent", "score": 3.8, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
            {"title": "Topic B", "url": "https://example.com/b", "summary": "B", "primary_domain": "ai-llm-agent", "score": 3.7, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
            {"title": "Topic C", "url": "https://example.com/c", "summary": "C", "primary_domain": "ai-llm-agent", "score": 3.6, "evidence_count": 1, "source_ids": ["hacker-news"], "tags": ["agent"]},
        ],
        analyses=[
            {"title": "Topic A", "url": "https://example.com/a", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic B", "url": "https://example.com/b", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic C", "url": "https://example.com/c", "primary_domain": "ai-llm-agent", "confidence": "low"},
        ],
        diagnostics=[],
        generated_at="2026-04-12T07:00:00+08:00",
        external_enrichment_fetcher=always_fail,
        external_enrichment_max_signals=3,
    )

    metrics = result["external_enrichment"]
    assert attempts == ["Topic A", "Topic B"]
    assert metrics["attempted"] == 2
    assert metrics["failed"] == 2
    assert metrics["skipped"] == 1
    assert metrics["circuit_open"] is True
    assert "circuit-open: Topic C" in metrics["reasons"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_intelligence.py::test_apply_intelligence_layer_tracks_external_enrichment_runtime_metrics tests/test_intelligence.py::test_apply_intelligence_layer_opens_circuit_after_two_consecutive_failures -q`

Expected: FAIL because `apply_intelligence_layer()` does not yet return `external_enrichment` metrics or open a circuit.

- [ ] **Step 3: Write minimal implementation**

```python
external_metrics = {
    "enabled": external_enrichment_fetcher is not None,
    "max_signals": max(0, external_enrichment_max_signals),
    "attempted": 0,
    "succeeded": 0,
    "failed": 0,
    "skipped": 0,
    "budget_used": 0,
    "success_rate": 0.0,
    "circuit_open": False,
    "reasons": [],
}
```

```python
if eligible and circuit_open:
    external_metrics["skipped"] += 1
    external_metrics["reasons"].append(f"circuit-open: {signal['title']}")
```

```python
result["external_enrichment"] = external_metrics
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_intelligence.py::test_apply_intelligence_layer_tracks_external_enrichment_runtime_metrics tests/test_intelligence.py::test_apply_intelligence_layer_opens_circuit_after_two_consecutive_failures -q`

Expected: PASS

### Task 2: Persist Enrichment Diagnostics In Run Status

**Files:**
- Modify: `src/auto_report/pipeline/run_once.py`
- Modify: `src/auto_report/app.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_build_run_status_includes_external_enrichment_metrics():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        external_enrichment={
            "enabled": True,
            "max_signals": 2,
            "attempted": 2,
            "succeeded": 1,
            "failed": 1,
            "skipped": 0,
            "budget_used": 2,
            "success_rate": 0.5,
            "circuit_open": False,
            "reasons": ["empty-result: Topic B"],
        },
    )

    assert status["external_enrichment"]["attempted"] == 2
    assert status["external_enrichment"]["success_rate"] == 0.5

def test_run_once_writes_external_enrichment_metrics_into_run_status(tmp_path, monkeypatch):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    sample_items = [
        CollectedItem(
            source_id="rss",
            item_id="1",
            title="Agent platform launched",
            url="https://example.com/agent-platform",
            summary="A new reasoning agent stack for enterprise deployment",
            published_at="2026-04-09T00:00:00+00:00",
            collected_at="2026-04-09T01:00:00+00:00",
            tags=["agent", "reasoning"],
            language="en",
            metadata={},
        )
    ]

    monkeypatch.setattr("auto_report.app.collect_all_items", lambda settings: (sample_items, ["测试诊断"]))
    monkeypatch.setattr("auto_report.app.send_pushplus", lambda *args, **kwargs: {"code": 200})
    monkeypatch.setenv("AUTO_PUSH_ENABLED", "false")

    run_once(tmp_path)

    status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
    assert "external_enrichment" in status
    assert status["external_enrichment"]["enabled"] in {True, False}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_run_once.py::test_build_run_status_includes_external_enrichment_metrics tests/test_run_once.py::test_run_once_writes_external_enrichment_metrics_into_run_status -q`

Expected: FAIL because `build_run_status()` does not accept `external_enrichment` and `run_once()` does not persist it.

- [ ] **Step 3: Write minimal implementation**

```python
def build_run_status(..., external_enrichment: dict[str, Any] | None = None) -> dict[str, object]:
    payload["external_enrichment"] = external_enrichment or {
        "enabled": False,
        "max_signals": 0,
        "attempted": 0,
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "budget_used": 0,
        "success_rate": 0.0,
        "circuit_open": False,
        "reasons": [],
    }
```

```python
external_enrichment = summary_payload.get("external_enrichment", {})
status = build_run_status(..., external_enrichment=external_enrichment)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_run_once.py::test_build_run_status_includes_external_enrichment_metrics tests/test_run_once.py::test_run_once_writes_external_enrichment_metrics_into_run_status -q`

Expected: PASS

### Task 3: Render External Enrichment In Private Ops Dashboard

**Files:**
- Modify: `src/auto_report/outputs/ops_dashboard.py`
- Modify: `tests/test_ops_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_ops_dashboard_renders_external_enrichment_section(tmp_path: Path):
    state_dir = tmp_path / "data" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "run-status.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-12T07:30:00+08:00",
                "pushed": False,
                "push_channel": "",
                "risk_level": "medium",
                "scheduler": {"trigger_kind": "schedule", "compensation_run": False},
                "delivery_results": {"successful_channels": [], "failed_channels": [], "skipped_channels": [], "channels": {}},
                "stage_status": {"analysis": "ok", "summary": "ok", "forecast": "ok"},
                "source_stats": {"collected_items": 8, "filtered_topics": 3},
                "timings": {"collection": 1.8, "rendering": 0.4},
                "external_enrichment": {
                    "enabled": True,
                    "max_signals": 2,
                    "attempted": 2,
                    "succeeded": 1,
                    "failed": 1,
                    "skipped": 1,
                    "budget_used": 2,
                    "success_rate": 0.5,
                    "circuit_open": True,
                    "reasons": ["empty-result: Topic B", "circuit-open: Topic C"],
                },
            }
        ),
        encoding="utf-8",
    )

    html = build_ops_dashboard(tmp_path).read_text(encoding="utf-8")
    assert "External Enrichment" in html
    assert "0.50" in html
    assert "Topic B" in html
    assert "open" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_ops_dashboard.py::test_build_ops_dashboard_renders_external_enrichment_section -q`

Expected: FAIL because the dashboard does not render the new section.

- [ ] **Step 3: Write minimal implementation**

```python
external = status.get("external_enrichment", {})
```

```python
<section class="panel">
  <h2>External Enrichment</h2>
  ...
</section>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_ops_dashboard.py::test_build_ops_dashboard_renders_external_enrichment_section -q`

Expected: PASS

### Task 4: Regression Verification

**Files:**
- Test: `tests/test_intelligence.py`
- Test: `tests/test_run_once.py`
- Test: `tests/test_ops_dashboard.py`

- [ ] **Step 1: Run targeted tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_intelligence.py tests/test_run_once.py tests/test_ops_dashboard.py -q`

Expected: PASS

- [ ] **Step 2: Run full suite**

Run: `$env:PYTHONPATH='src'; python -m pytest tests -q`

Expected: PASS

- [ ] **Step 3: Record notes in docs**

```text
- external enrichment observability is private-only
- circuit breaker is single-run only
- success rate is run-scoped, not historical
```
