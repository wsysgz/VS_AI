# High-Value Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add second-stage enrichment for high-value themes by attaching related supporting evidence from the current collection run, then surface that evidence in report payloads and rendered outputs.

**Architecture:** Extend the existing intelligence layer instead of creating a parallel pipeline. `analysis.py` will pass raw collected items into the intelligence stage, which will compute support evidence for high-score signals from preferred source types (`official`, `repo`, `paper`) using lightweight title-token matching and source priority. Briefing and renderers will expose the new support evidence without changing delivery-channel contracts.

**Tech Stack:** Python 3.14, pytest, existing `auto_report` pipeline modules, JSON/Markdown/HTML renderers.

---

### Task 1: Add Enrichment Discovery In Intelligence Layer

**Files:**
- Modify: `src/auto_report/pipeline/intelligence.py`
- Modify: `src/auto_report/pipeline/analysis.py`
- Test: `tests/test_intelligence.py`

- [ ] **Step 1: Write the failing test**

```python
def test_apply_intelligence_layer_attaches_related_support_evidence(tmp_path: Path):
    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[{
            "title": "Launch HN: Agent debugger",
            "url": "https://news.ycombinator.com/item?id=1",
            "summary": "Community launch post",
            "primary_domain": "ai-llm-agent",
            "score": 3.3,
            "evidence_count": 1,
            "source_ids": ["hacker-news"],
            "tags": ["show-hn"],
        }],
        analyses=[{
            "title": "Launch HN: Agent debugger",
            "url": "https://news.ycombinator.com/item?id=1",
            "primary_domain": "ai-llm-agent",
            "confidence": "low",
        }],
        items=[
            CollectedItem(
                source_id="openai-news",
                item_id="official-1",
                title="OpenAI launches agent debugger",
                url="https://openai.com/news/agent-debugger",
                summary="Official release note for the debugger runtime.",
                published_at="2026-04-11T00:00:00+08:00",
                collected_at="2026-04-11T00:10:00+08:00",
                tags=["release"],
                language="en",
                metadata={},
            )
        ],
        diagnostics=[],
        generated_at="2026-04-11T07:00:00+08:00",
    )

    support = result["signals"][0]["enrichment"]["support_evidence"]
    assert support[0]["source_type"] == "official"
    assert support[0]["title"] == "OpenAI launches agent debugger"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_intelligence.py::test_apply_intelligence_layer_attaches_related_support_evidence -q`
Expected: FAIL because `apply_intelligence_layer()` does not yet accept `items` or populate `support_evidence`

- [ ] **Step 3: Write minimal implementation**

```python
def _collect_support_evidence(signal: dict[str, object], items: list[CollectedItem]) -> list[dict[str, object]]:
    # Prefer official/repo/paper evidence with overlapping title tokens.
    ...

def apply_intelligence_layer(..., items: list[CollectedItem] | None = None, ...):
    support_evidence = _collect_support_evidence(signal, items or [])
    enrichment["support_evidence"] = support_evidence
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_intelligence.py::test_apply_intelligence_layer_attaches_related_support_evidence -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/pipeline/intelligence.py src/auto_report/pipeline/analysis.py tests/test_intelligence.py
git commit -m "feat: add related evidence enrichment"
```

### Task 2: Surface Support Evidence In Briefing And Renderers

**Files:**
- Modify: `src/auto_report/pipeline/briefing.py`
- Modify: `src/auto_report/outputs/renderers.py`
- Test: `tests/test_briefing.py`
- Test: `tests/test_renderers.py`

- [ ] **Step 1: Write the failing tests**

```python
assert brief["topic_briefs"][0]["support_evidence"][0]["source_type"] == "official"
assert "OpenAI launches agent debugger" in report
assert "support evidence" in html or "交叉印证" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/test_briefing.py tests/test_renderers.py -q`
Expected: FAIL because briefing/renderers do not yet expose the support-evidence list

- [ ] **Step 3: Write minimal implementation**

```python
briefs.append({
    ...,
    "support_evidence": analysis.get("support_evidence", []),
})
```

```python
for evidence in topic["support_evidence"][:3]:
    lines.append(f"- 佐证：{evidence['source_type']} | {evidence['title']} | {evidence['url']}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/test_briefing.py tests/test_renderers.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/pipeline/briefing.py src/auto_report/outputs/renderers.py tests/test_briefing.py tests/test_renderers.py
git commit -m "feat: render support evidence for enriched themes"
```

### Task 3: Full Regression Verification

**Files:**
- Test: `tests/`

- [ ] **Step 1: Run the targeted intelligence/rendering tests**

Run: `PYTHONPATH=src python -m pytest tests/test_intelligence.py tests/test_analysis.py tests/test_briefing.py tests/test_renderers.py -q`
Expected: PASS

- [ ] **Step 2: Run the full test suite**

Run: `PYTHONPATH=src python -m pytest tests -q`
Expected: PASS with no failures

- [ ] **Step 3: Record execution notes**

```text
- support_evidence only uses current-run collected items
- no online fetches are added in this slice
- future work can add release-note / issue / paper fetchers on top
```
