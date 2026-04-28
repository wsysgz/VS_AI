# Public Site IA V2 Batch 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add direct filtering to the `赛道` and `来源` index pages, tighten mobile navigation and card layout behavior, and update the repo docs so IA V2 status matches the current implementation truth.

**Architecture:** Keep all public-site behavior inside `src/auto_report/outputs/pages_builder.py`, reusing the existing inline CSS and static client-side filtering pattern already used by the archives page. Use TDD for each behavior change, keep the generated Pages model unchanged, and finish with a local rebuild plus roadmap/handoff doc refresh.

**Tech Stack:** Python static HTML generation, inline CSS/JS, pytest, generated `docs/` Pages output.

---

## File Map

- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `tests/test_pages_builder.py`
- Modify: `V1升级方案.md`
- Modify: `交接备忘录.md`
- Modify: `AI对接手册.md`

### Task 1: Add Failing Tests For Track/Source Filtering

**Files:**
- Modify: `tests/test_pages_builder.py`
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Write the failing tests**

Add these tests near the existing IA V2 Pages tests in `tests/test_pages_builder.py`:

```python
def test_build_pages_site_tracks_index_includes_filter_search(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    tracks_index = (tmp_path / "docs" / "tracks" / "index.html").read_text(encoding="utf-8")

    assert 'id="track-filter-search"' in tracks_index
    assert "筛选赛道" in tracks_index
    assert "trackFilterSearch" in tracks_index


def test_build_pages_site_sources_index_includes_filter_search(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    sources_index = (tmp_path / "docs" / "sources" / "index.html").read_text(encoding="utf-8")

    assert 'id="source-filter-search"' in sources_index
    assert "筛选来源" in sources_index
    assert "sourceFilterSearch" in sources_index


def test_build_pages_site_track_and_source_cards_expose_searchable_text(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    tracks_index = (tmp_path / "docs" / "tracks" / "index.html").read_text(encoding="utf-8")
    sources_index = (tmp_path / "docs" / "sources" / "index.html").read_text(encoding="utf-8")

    assert 'data-search=' in tracks_index
    assert 'data-search=' in sources_index
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_tracks_index_includes_filter_search tests/test_pages_builder.py::test_build_pages_site_sources_index_includes_filter_search tests/test_pages_builder.py::test_build_pages_site_track_and_source_cards_expose_searchable_text -q
```

Expected: FAIL because the tracks/sources index pages currently do not render the new filter inputs, scripts, or searchable card metadata.

- [ ] **Step 3: Write the minimal implementation**

In `src/auto_report/outputs/pages_builder.py`, update the card renderers so searchable text is available on the card element itself:

```python
def _track_summary_cards(tracks: list[dict[str, object]], link_prefix: str = "./") -> str:
    cards = []
    for track in tracks:
        search_text = " ".join(
            [
                _safe_text(track.get("name")),
                _safe_text(track.get("latest_title")),
            ]
        ).strip()
        cards.append(
            f"""<article class="archive-card" data-search="{html.escape(search_text)}">
  <span class="eyebrow">赛道</span>
  <h3>{html.escape(str(track["name"]))}</h3>
  <p>{int(track["count"])} 条信号 · 最近 {_format_date(str(track["latest_date"]))}</p>
  <div class="archive-footer">
    <span>{html.escape(str(track["latest_title"]))}</span>
    <a href="{html.escape(_href(track["archive_url"], link_prefix))}">打开赛道</a>
  </div>
</article>"""
        )
    return "".join(cards) or '<article class="archive-card"><h3>暂无赛道</h3><p>等待下一次日报生成。</p></article>'
```

```python
def _source_summary_cards(sources: list[dict[str, object]], link_prefix: str = "./") -> str:
    cards = []
    for source in sources:
        top_tracks = [str(track_name) for track_name in list(source.get("top_tracks", []))[:2]]
        search_text = " ".join(
            [
                _safe_text(source.get("name")),
                _safe_text(source.get("latest_title")),
                *top_tracks,
            ]
        ).strip()
        track_tags = "".join(
            f'<span class="tag alt">{html.escape(str(track_name))}</span>'
            for track_name in top_tracks
        )
        cards.append(
            f"""<article class="archive-card" data-search="{html.escape(search_text)}">
  <span class="eyebrow">来源</span>
  <h3>{html.escape(str(source["name"]))}</h3>
  <p>{int(source["count"])} 条信号 · {int(source["report_count"])} 份日报 · 最近 {_format_date(str(source["latest_date"]))}</p>
  <div class="archive-meta" style="margin-top:12px;">{track_tags}</div>
  <p class="subtle" style="margin-top:12px;">{html.escape(_localize_known_text(source["latest_title"]))}</p>
  <a class="article-action" href="{html.escape(_href(source["archive_url"], link_prefix))}">打开来源</a>
</article>"""
        )
    return "".join(cards) or '<article class="archive-card"><h3>暂无来源</h3><p>等待下一次日报生成。</p></article>'
```

Then add filter inputs and small inline scripts to `_build_tracks_index()` and `_build_sources_index()`:

```python
    <section class="section">
      <div class="search-shell">
        <input id="track-filter-search" class="filter-search" type="search" placeholder="筛选赛道">
      </div>
      <div id="tracks-grid" class="archive-grid">
        {_track_summary_cards(track_summaries, link_prefix="../")}
      </div>
    </section>
```

```python
  <script>
    const trackCards = [...document.querySelectorAll("#tracks-grid .archive-card")];
    const trackFilterSearch = document.getElementById("track-filter-search");
    if (trackFilterSearch) {
      trackFilterSearch.addEventListener("input", () => {
        const query = trackFilterSearch.value.trim().toLowerCase();
        trackCards.forEach((card) => {
          const value = (card.dataset.search || card.textContent || "").toLowerCase();
          card.style.display = !query || value.includes(query) ? "" : "none";
        });
      });
    }
  </script>
```

Apply the same structure for `_build_sources_index()` using `sourceCards`, `sourceFilterSearch`, and `#sources-grid`.

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_tracks_index_includes_filter_search tests/test_pages_builder.py::test_build_pages_site_sources_index_includes_filter_search tests/test_pages_builder.py::test_build_pages_site_track_and_source_cards_expose_searchable_text -q
```

Expected: PASS.

### Task 2: Add Failing Tests For Mobile CSS Tightening

**Files:**
- Modify: `tests/test_pages_builder.py`
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Write the failing tests**

Add these tests in `tests/test_pages_builder.py`:

```python
def test_build_pages_site_mobile_css_tightens_nav_chip_and_grid_layout(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 880px)" in index_html
    assert ".hero-meta" in index_html
    assert "@media (max-width: 640px)" in index_html
    assert "grid-template-columns: 1fr;" in index_html
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_mobile_css_tightens_nav_chip_and_grid_layout -q
```

Expected: FAIL because the generated CSS does not yet include the new small-screen tightening rules and `640px` breakpoint.

- [ ] **Step 3: Write the minimal implementation**

In `_base_css()` inside `src/auto_report/outputs/pages_builder.py`, extend the responsive rules:

```python
  @media (max-width: 880px) {
    .site-shell { padding: 0 14px 36px; }
    .topbar { grid-template-columns: 1fr; gap: 10px; }
    .nav-links { justify-content: flex-start; gap: 10px; }
    .hero-meta { gap: 6px; }
    .workbench { grid-template-columns: 1fr; }
    .panel, .section { padding: 18px; }
    .page-title { font-size: 28px; }
    .lead { font-size: 16px; }
    .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .signal-grid,
    .archive-grid,
    .summary-grid,
    .comparison-grid { grid-template-columns: 1fr; }
    .signal-footer,
    .archive-footer {
      align-items: flex-start;
      flex-direction: column;
    }
  }
  @media (max-width: 640px) {
    .nav-links { gap: 8px; font-size: 13px; }
    .chip,
    .tag { min-height: 28px; padding: 4px 9px; }
    .hero-meta,
    .meta-row,
    .archive-meta,
    .feed-links { gap: 6px; }
    .archive-card,
    .article-card,
    .signal,
    .summary-card,
    .topic-card { padding: 14px; }
  }
  @media (max-width: 420px) {
    .stats-grid { grid-template-columns: 1fr; }
    .nav-links { gap: 8px; }
  }
```

Keep the CSS consistent with the current visual language. Do not add new classes when the existing ones already cover the elements.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_mobile_css_tightens_nav_chip_and_grid_layout -q
```

Expected: PASS.

### Task 3: Refresh IA V2 Status In Handoff And Roadmap Docs

**Files:**
- Modify: `V1升级方案.md`
- Modify: `交接备忘录.md`
- Modify: `AI对接手册.md`

- [ ] **Step 1: Write the failing documentation checks**

Add a documentation regression test in `tests/test_pages_builder.py` only if the repo already tests docs text directly. Otherwise, use a manual grep check instead of forcing an unrelated test harness.

Use these manual checks first:

```powershell
rg -n "IA V2 第二批评估|再评估 IA V2 第二批|已本地完成|第三批" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected before edits: docs still describe batch 2 as evaluation or next-step work rather than a completed local batch.

- [ ] **Step 2: Update the roadmap doc**

In `V1升级方案.md`, replace the current batch-2 wording with status that matches repo truth:

```md
- [x] 公开站 IA V2 第二批已本地完成：日报入口、最近归档扩到 8 篇、来源总览页、来源详情页、赛道/来源交叉视图均已落地并完成本地验证
- [ ] 公开站 IA V2 第三批：赛道/来源列表页检索与移动端导航/卡片压缩体验
```

Also update any “当前待推进” or “下一阶段建议顺序” section that still treats batch 2 as only an evaluation item.

- [ ] **Step 3: Update the handoff doc**

In `交接备忘录.md`, update the short-status, current-mainline, and next-step sections so they describe:

```md
- 当前主线：`公开站 IA V2 第一批已远端确认；第二批已本地完成并通过本地验证；当前进入第三批（赛道/来源检索 + 移动端体验）`
```

Also replace any “再评估 IA V2 第二批” phrasing in the “如果下一位只剩 3 分钟” section with batch-3 wording.

- [ ] **Step 4: Update the AI handoff manual**

In `AI对接手册.md`, update the `60 秒接管` and `当前项目进度` sections so they say:

```md
- 当前主线优先级：`公开站 IA V2 第一批已完成、已推送、已远端确认；第二批已本地完成；当前推进第三批（赛道/来源检索与移动端体验）`
```

Also replace any remaining batch-2-next wording in the “下次接手第一条动作” and “默认优先顺序” sections.

- [ ] **Step 5: Run grep to verify doc status is consistent**

Run:

```powershell
rg -n "IA V2 第二批评估|再评估 IA V2 第二批" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected: no matches.

Then confirm the new batch-3 wording exists:

```powershell
rg -n "第二批已本地完成|第三批|赛道/来源检索|移动端体验" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected: matches in all three files.

### Task 4: Run Pages-Focused Verification And Rebuild

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `tests/test_pages_builder.py`
- Generated: `docs/index.html`
- Generated: `docs/tracks/index.html`
- Generated: `docs/sources/index.html`

- [ ] **Step 1: Run the Pages builder tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py -q
```

Expected: PASS.

- [ ] **Step 2: Rebuild the Pages output**

Run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-pages
```

Expected:

```text
[Pages] Site built at D:\GitHub\auto\docs
[Pages] Index: D:\GitHub\auto\docs\index.html
```

- [ ] **Step 3: Run full verification**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Visually inspect the local preview**

Check:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/tracks/
http://127.0.0.1:8765/sources/
```

Verify:

- `赛道` page exposes the filter input and narrows cards
- `来源` page exposes the filter input and narrows cards
- homepage/top-level navigation wraps cleanly on narrow widths
- cards remain readable and buttons stay tappable

- [ ] **Step 5: Record remaining risk**

If the static checks pass but only light visual inspection was performed, note that residual risk is limited to small-screen layout polish rather than data or generator correctness.
