# Dual-Track Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `auto / reviewed` publication modes that can coexist in report outputs, run status, workflows, and public Pages selection.

**Architecture:** Keep one shared analysis/rendering pipeline, but thread an explicit `publication_mode` through CLI, settings, runtime metadata, and file naming. Preserve legacy `latest-summary.*` compatibility while adding mode-scoped files and making Pages prefer `reviewed` for the public latest view.

**Tech Stack:** Python 3.14, pytest, GitHub Actions workflows, existing `auto_report` app/output modules, Markdown docs.

---

### Task 1: Lock The Publication-Mode Contract In Tests

**Files:**
- Modify: `tests/test_cli_smoke.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
args = parser.parse_args(["run-once", "--publication-mode", "reviewed"])
assert args.publication_mode == "reviewed"
```

```python
monkeypatch.setenv("PUBLICATION_MODE", "reviewed")
settings = load_settings(Path.cwd())
assert settings.env["PUBLICATION_MODE"] == "reviewed"
```

```python
status = build_run_status(
    generated_files=["data/reports/latest-summary-reviewed.md"],
    pushed=False,
    publication_mode="reviewed",
)
assert status["publication_mode"] == "reviewed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_cli_smoke.py tests/test_settings.py tests/test_run_once.py -q`
Expected: FAIL because CLI/settings/run-status do not yet expose `publication_mode`.

- [ ] **Step 3: Write minimal implementation**

```python
run_once_parser.add_argument("--publication-mode", choices=("auto", "reviewed"), default="")
```

```python
"PUBLICATION_MODE": os.environ.get("PUBLICATION_MODE", "auto"),
```

```python
def build_run_status(..., publication_mode: str = "auto", ...):
    payload["publication_mode"] = publication_mode
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_cli_smoke.py tests/test_settings.py tests/test_run_once.py -q`
Expected: PASS

### Task 2: Write Mode-Scoped Outputs And Mode-Aware Delivery Links

**Files:**
- Modify: `src/auto_report/app.py`
- Modify: `tests/test_run_once.py`

- [ ] **Step 1: Write the failing tests**

```python
generated_files, _, _ = render_reports(tmp_path, publication_mode="reviewed")
assert any(path.endswith("latest-summary-reviewed.json") for path in generated_files)
payload = json.loads((tmp_path / "data" / "reports" / "latest-summary-reviewed.json").read_text(encoding="utf-8"))
assert payload["meta"]["publication_mode"] == "reviewed"
```

```python
run_once(tmp_path, publication_mode="reviewed")
status = json.loads((tmp_path / "data" / "state" / "run-status.json").read_text(encoding="utf-8"))
assert status["publication_mode"] == "reviewed"
assert "latest-summary-reviewed.md" in status["generated_files"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_run_once.py -q`
Expected: FAIL because reports do not yet write track-specific outputs or persist `publication_mode`.

- [ ] **Step 3: Write minimal implementation**

```python
def _resolve_publication_mode(requested: str, settings) -> str:
    mode = (requested or settings.env.get("PUBLICATION_MODE", "auto")).strip().lower()
    return "reviewed" if mode == "reviewed" else "auto"
```

```python
summary_payload["meta"]["publication_mode"] = publication_mode
track_prefix = f"latest-summary-{publication_mode}"
archive_suffix = f"summary-{publication_mode}"
```

```python
def _build_detail_url(settings, publication_mode: str) -> str:
    return f"{base_url}/blob/main/data/reports/latest-summary-{publication_mode}.md"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_run_once.py -q`
Expected: PASS

### Task 3: Make Pages And Workflows Understand The Two Tracks

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `.github/workflows/collect-report.yml`
- Modify: `.github/workflows/backfill-report.yml`
- Modify: `.github/workflows/reusable-report.yml`
- Modify: `.github/workflows/reusable-backfill.yml`
- Modify: `tests/test_pages_builder.py`
- Modify: `tests/test_workflows.py`

- [ ] **Step 1: Write the failing tests**

```python
assert "人工复核版" in index_html
assert "OpenAI reviewed judgment" in index_html
```

```python
assert inputs["publication_mode"]["type"] == "string"
assert "PUBLICATION_MODE: ${{ inputs.publication_mode }}" in content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_pages_builder.py tests/test_workflows.py -q`
Expected: FAIL because Pages do not yet prefer reviewed outputs and workflows do not yet pass mode inputs.

- [ ] **Step 3: Write minimal implementation**

```python
mode_rank = {"reviewed": 1, "auto": 0}
```

```python
publication_mode:
  required: true
  type: string
```

```python
PUBLICATION_MODE: ${{ inputs.publication_mode }}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_pages_builder.py tests/test_workflows.py -q`
Expected: PASS

### Task 4: Align Docs And Upgrade Status

**Files:**
- Modify: `README.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/USER_GUIDE.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/OPS_RUNBOOK.md`
- Modify: `docs/upgrade-plan/V7_状态矩阵_2026-04-11.md`

- [ ] **Step 1: Update wording to match implementation**

```text
scheduled runs stay auto
manual reruns/backfills can publish reviewed
Pages prefers reviewed when both tracks exist
```

- [ ] **Step 2: Verify doc wording stays consistent**

Run: `rg -n "reviewed|publication_mode|人工复核版|双轨发布" README.md docs`
Expected: README, runbook, handoff, and state matrix tell the same story.

### Task 5: Full Verification

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run focused contract tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_cli_smoke.py tests/test_settings.py tests/test_run_once.py tests/test_pages_builder.py tests/test_workflows.py -q`
Expected: PASS

- [ ] **Step 2: Run workflow validation**

Run: `pwsh ./scripts/check-workflows.ps1`
Expected: PASS

- [ ] **Step 3: Run full suite**

Run: `$env:PYTHONPATH='src'; python -m pytest tests -q`
Expected: PASS

- [ ] **Step 4: Record execution notes**

```text
- dual-track publishing now supports auto + reviewed side by side
- reviewed track is preferred by public Pages when both exist
- scheduled workflow remains auto by default; manual runs can switch to reviewed
```
