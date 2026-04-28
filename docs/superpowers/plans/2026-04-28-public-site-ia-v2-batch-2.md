# Public Site IA V2 Batch 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class source browsing layer to the public site with `/sources/`, per-source detail pages, and source summaries inside track pages.

**Architecture:** Keep all generation inside `src/auto_report/outputs/pages_builder.py`. Derive source summaries from normalized report signals already used for archives, tracks, weekly pages, and search index. Reuse the existing static card layout so the new source surfaces fit the current Pages IA without introducing runtime code or a frontend framework.

**Tech Stack:** Python static HTML generation, pytest, generated `docs/` Pages output, existing inline CSS/JS in `pages_builder.py`.

---

## File Map

- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `tests/test_pages_builder.py`
- Create: `docs/sources/index.html`
- Create: `docs/sources/<slug>/index.html`

## Task 1: Add Source Summary Model

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_pages_site_generates_sources_index_and_detail_pages(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    sources_index = (tmp_path / "docs" / "sources" / "index.html").read_text(encoding="utf-8")
    detail_pages = list((tmp_path / "docs" / "sources").glob("*/index.html"))

    assert "来源" in sources_index
    assert "news.example.com" in sources_index
    assert detail_pages
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_sources_index_and_detail_pages -q
```

Expected: FAIL because `docs/sources/index.html` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def _build_source_summaries(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for report in reports:
        seen_keys: set[str] = set()
        for signal in report["signals"]:
            source_name = _safe_text(signal.get("source"))
            if not source_name:
                continue
            row = summaries.setdefault(
                source_name,
                {
                    "name": source_name,
                    "slug": _slugify(source_name),
                    "count": 0,
                    "report_count": 0,
                    "latest_date": str(report["date"]),
                    "latest_title": str(signal["title"]),
                    "track_counts": Counter(),
                    "archive_url": f"sources/{_slugify(source_name)}/",
                },
            )
            row["count"] = int(row["count"]) + 1
            row["track_counts"][str(signal["domain_label"])] += 1
            if source_name not in seen_keys:
                row["report_count"] = int(row["report_count"]) + 1
                seen_keys.add(source_name)
            if str(report["date"]) >= str(row["latest_date"]):
                row["latest_date"] = str(report["date"])
                row["latest_title"] = str(signal["title"])
    return sorted(summaries.values(), key=lambda item: (-int(item["count"]), str(item["name"])))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_sources_index_and_detail_pages -q
```

Expected: PASS.

## Task 2: Build `/sources/` And Per-Source Detail Pages

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_pages_site_source_pages_show_tracks_reports_and_signals(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    source_page = next((tmp_path / "docs" / "sources").glob("*/index.html")).read_text(encoding="utf-8")

    assert "覆盖赛道" in source_page
    assert "最近日报" in source_page
    assert "重点信号" in source_page
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_source_pages_show_tracks_reports_and_signals -q
```

Expected: FAIL because the source detail template lacks these sections.

- [ ] **Step 3: Write minimal implementation**

```python
def _reports_for_source(source: dict[str, object], reports: list[dict[str, object]]) -> list[dict[str, object]]:
    return [report for report in reports if _safe_text(source["name"]) in report["source_counts"]]


def _signals_for_source(source: dict[str, object], reports: list[dict[str, object]]) -> list[dict[str, object]]:
    values: list[dict[str, object]] = []
    for report in reports:
        for signal in report["signals"]:
            if _safe_text(signal.get("source")) == _safe_text(source["name"]):
                values.append(signal)
    return values[:8]


def _build_source_page(source: dict[str, object], reports: list[dict[str, object]]) -> str:
    source_reports = _reports_for_source(source, reports)
    source_signals = _signals_for_source(source, reports)
    # Render headline stats, covered tracks, recent daily reports, top signals
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_source_pages_show_tracks_reports_and_signals -q
```

Expected: PASS.

## Task 3: Add Source Navigation And Track/Source Cross View

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_pages_site_navigation_and_track_pages_link_sources(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    home_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    track_html = next((tmp_path / "docs" / "tracks").glob("*/index.html")).read_text(encoding="utf-8")

    assert 'href="./sources/"' in home_html
    assert "活跃来源" in track_html
    assert "打开来源" in track_html
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_navigation_and_track_pages_link_sources -q
```

Expected: FAIL because homepage nav and track pages do not surface the new source layer.

- [ ] **Step 3: Write minimal implementation**

```python
def _sources_for_track(track: dict[str, object], reports: list[dict[str, object]], source_summaries: list[dict[str, object]]) -> list[dict[str, object]]:
    allowed = {
        _safe_text(signal.get("source"))
        for report in reports
        for signal in report["signals"]
        if _signal_matches_track(signal, track)
    }
    return [source for source in source_summaries if _safe_text(source["name"]) in allowed][:6]


def _source_summary_cards(sources: list[dict[str, object]], link_prefix: str = "./") -> str:
    # Render source card with top tracks, latest date, and "打开来源" action
```

Also wire `来源` links into homepage, archives, daily, tracks, weekly, special, day, article, brief, and source pages.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_navigation_and_track_pages_link_sources -q
```

Expected: PASS.

## Task 4: Rebuild And Verify

**Files:**
- Generated: `docs/index.html`
- Generated: `docs/sources/index.html`
- Generated: `docs/sources/<slug>/index.html`

- [ ] **Step 1: Run targeted Pages tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py -q
```

Expected: PASS.

- [ ] **Step 2: Build Pages**

Run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

Expected:

```text
[Pages] Site built at D:\GitHub\auto\docs
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Browser review**

Check:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/sources/
http://127.0.0.1:8765/tracks/
```

Verify:

- homepage has a visible `来源` entry
- `/sources/` lists source cards
- track detail pages expose active sources
- source detail pages show covered tracks, daily reports, and top signals

