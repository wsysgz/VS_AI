# Public Site IA V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the public Pages site from a chronological report archive into a clearer operating surface for daily reading, track browsing, and source review.

**Implementation status:** Completed locally on 2026-04-28. Pages IA V2 first batch now includes `/tracks/`, per-track detail pages, archive source search, and cross-page track navigation. Verification covered targeted Pages tests, full pytest, workflow guard, prompt eval, reviewed `run-once` with `AI_DISABLE_LLM=true`, Pages build, ops dashboard, source governance, review queue, and browser preview at `http://127.0.0.1:8765/`.

**Architecture:** Keep the current static generator in `src/auto_report/outputs/pages_builder.py`; do not introduce a frontend framework or runtime service. Generate new IA from existing report payloads, search index, weekly aggregates, special collections, and source/domain counts so Pages remains reproducible in CI.

**Tech Stack:** Python static HTML generation, pytest, generated `docs/` Pages output, existing inline CSS/JS in `pages_builder.py`.

---

## Current Findings

- Latest remote release confirmation is green: `Collect And Report` run `25007010720`.
- Local watch runner was refreshed on 2026-04-28; `blocked_count=0`, `changed_count=1`.
- `cerebras-blog` produced one new watch item, `Figma - MultiAgents`, and the latest report already contains it, so no source hotfix is required.
- `renesas-blog` remains intentionally disabled with `watch_strategy: disabled`; keep observing, do not expand sources in this phase.
- Public site first-pass fixes are done: safe search rendering, safe links, favicon, and search tag de-duplication.
- Biggest IA issue now visible from generated `docs/archives/index.html`: archive source filters render a very large ungrouped button wall, making source browsing noisy.

## Frontend Direction

**Visual thesis:** Quiet intelligence-console layout: dense, scannable, low-chrome, with clear rails for time, track, and source.

**Content plan:** Homepage stays an operational workbench; archives become a filterable history surface; new track/source views provide structured entry points; weekly/special pages remain secondary deep-dive surfaces.

**Interaction thesis:** Use search/filter controls that reduce visible clutter, make track/source navigation persistent, and keep all interactions static-page compatible.

## Task 1: Add IA Helper Model For Tracks And Sources

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [x] **Step 1: Write tests for derived track/source summaries**

Add a test near the existing Pages builder tests:

```python
def test_build_pages_site_generates_track_and_source_navigation(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    tracks_index = (tmp_path / "docs" / "tracks" / "index.html").read_text(encoding="utf-8")

    assert "赛道" in index_html
    assert "来源" in index_html
    assert "AI/智能体" in tracks_index
    assert "AI × 电子" in tracks_index
```

- [x] **Step 2: Run the failing test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_track_and_source_navigation -q
```

Expected: fail because `docs/tracks/index.html` does not exist.

- [x] **Step 3: Add helper functions**

Add helpers in `pages_builder.py` near the existing collection helpers:

```python
def _build_track_summaries(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries: dict[str, dict[str, object]] = {}
    for report in reports:
        for domain, count in report["domain_counts"].items():
            row = summaries.setdefault(
                str(domain),
                {
                    "name": str(domain),
                    "count": 0,
                    "latest_date": str(report["date"]),
                    "latest_title": str(report["judgment"]),
                    "archive_url": f"tracks/{_slugify(str(domain))}/",
                },
            )
            row["count"] = int(row["count"]) + int(count)
            if str(report["date"]) > str(row["latest_date"]):
                row["latest_date"] = str(report["date"])
                row["latest_title"] = str(report["judgment"])
    return sorted(summaries.values(), key=lambda item: (-int(item["count"]), str(item["name"])))
```

Use the existing `_slugify()` helper if present; if it is not present, add a local helper that keeps ASCII slugs and falls back to a stable hash for non-ASCII labels.

- [x] **Step 4: Generate `/tracks/` index**

Add `_build_tracks_index(track_summaries)` and wire it inside `build_pages_site()`:

```python
tracks_dir = docs_dir / "tracks"
tracks_dir.mkdir(parents=True, exist_ok=True)
(tracks_dir / "index.html").write_text(_build_tracks_index(track_summaries), encoding="utf-8")
```

- [x] **Step 5: Verify test passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_track_and_source_navigation -q
```

Expected: `1 passed`.

## Task 2: Reduce Archive Filter Clutter

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [x] **Step 1: Write archive-filter ergonomics test**

Add:

```python
def test_build_pages_site_archive_filters_include_source_search(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    archive_index = (tmp_path / "docs" / "archives" / "index.html").read_text(encoding="utf-8")

    assert 'id="source-filter-search"' in archive_index
    assert "筛选来源" in archive_index
    assert "sourceFilterSearch" in archive_index
```

- [x] **Step 2: Run the failing test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_archive_filters_include_source_search -q
```

Expected: fail because archive source filtering has no search box.

- [x] **Step 3: Add source filter search input**

In `_build_archives_index()`, insert before source buttons:

```html
<input id="source-filter-search" type="search" placeholder="筛选来源">
```

Add static JS:

```javascript
const sourceFilterSearch = document.getElementById("source-filter-search");
if (sourceFilterSearch) {
  sourceFilterSearch.addEventListener("input", () => {
    const query = sourceFilterSearch.value.trim().toLowerCase();
    document.querySelectorAll('button[data-kind="source"]').forEach((button) => {
      const value = (button.dataset.value || button.textContent || "").toLowerCase();
      button.style.display = !query || value.includes(query) ? "" : "none";
    });
  });
}
```

- [x] **Step 4: Verify archive filter test passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_archive_filters_include_source_search -q
```

Expected: `1 passed`.

## Task 3: Add Track Detail Pages

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [x] **Step 1: Write track detail page test**

Add:

```python
def test_build_pages_site_generates_track_detail_pages(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    tracks_root = tmp_path / "docs" / "tracks"
    detail_pages = list(tracks_root.glob("*/index.html"))

    assert detail_pages
    detail_html = detail_pages[0].read_text(encoding="utf-8")
    assert "最近日报" in detail_html
    assert "重点信号" in detail_html
```

- [x] **Step 2: Run the failing test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_track_detail_pages -q
```

Expected: fail until detail pages are generated.

- [x] **Step 3: Generate per-track pages**

Add `_build_track_page(track, reports)` and write each page under `docs/tracks/<slug>/index.html`. Each page should show:

- track name
- latest report cards that include the track
- top signals from those reports where `primary_domain` or tag data matches the track
- links back to archive/day pages

- [x] **Step 4: Verify track detail test passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_track_detail_pages -q
```

Expected: `1 passed`.

## Task 4: Wire Navigation Across Pages

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [x] **Step 1: Add navigation regression test**

Add:

```python
def test_build_pages_site_navigation_links_tracks_everywhere(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    pages = [
        tmp_path / "docs" / "index.html",
        tmp_path / "docs" / "archives" / "index.html",
        tmp_path / "docs" / "weekly" / "index.html",
        tmp_path / "docs" / "special" / "index.html",
    ]
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert "tracks/" in html
        assert "赛道" in html
```

- [x] **Step 2: Run the failing test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_navigation_links_tracks_everywhere -q
```

Expected: fail until nav links are wired.

- [x] **Step 3: Update nav blocks**

Add a `赛道` nav link to homepage, archive, weekly, special, day, article, and brief pages. Keep relative paths correct per page depth.

- [x] **Step 4: Verify navigation test passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_navigation_links_tracks_everywhere -q
```

Expected: `1 passed`.

## Task 5: Build And Review Public Output

**Files:**
- Generated: `docs/`
- Generated: `docs/tracks/`

- [x] **Step 1: Run targeted Pages tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py -q
```

Expected: Pages tests pass.

- [x] **Step 2: Build Pages**

Run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

Expected output includes:

```text
[Pages] Site built at D:\GitHub\auto\docs
```

- [x] **Step 3: Start preview and inspect**

Run a static server from `docs/` and send the URL directly to the user. Check:

- homepage has a visible `赛道` entry
- `/tracks/` opens
- at least one track detail page opens
- archive source filter can narrow the button wall
- mobile width does not overlap text or navigation

- [x] **Step 4: Run full verification if code changes are kept**

Run:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
python -m pytest tests -q
```

Expected: workflow guard passes; full test suite passes.

## Completion Criteria

- Public site has first-class track browsing.
- Archive source filter no longer forces users to scan a huge ungrouped source wall.
- Existing homepage, archives, weekly, special, article, and search behaviors remain covered by tests.
- Generated Pages output is locally previewed before any remote release confirmation.
