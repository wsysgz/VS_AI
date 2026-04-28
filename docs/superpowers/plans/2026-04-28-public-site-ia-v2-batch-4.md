# Public Site IA V2 Batch 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the public-site IA V2 closeout by making the homepage route read as `今日判断 -> 赛道 / 来源`, making `重点信号` the first action on track/source detail pages, and recording that `日报 / 周报 / 专题` are secondary entry points before switching back to earlier tail items.

**Architecture:** Keep all public-site generation inside `src/auto_report/outputs/pages_builder.py`; reuse the existing static HTML, inline CSS, card helpers, and generated `docs/` output model. Use focused pytest assertions in `tests/test_pages_builder.py` before changing templates, then rebuild Pages and refresh handoff docs. Do not introduce a frontend framework, new runtime data schema, or new top-level page type.

**Tech Stack:** Python static HTML generation, inline CSS/JS, pytest, generated GitHub Pages files under `docs/`, PowerShell local verification.

---

## File Map

- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `tests/test_pages_builder.py`
- Modify: `V1升级方案.md`
- Modify: `交接备忘录.md`
- Modify: `AI对接手册.md`
- Generated after rebuild: `docs/index.html`
- Generated after rebuild: `docs/tracks/index.html`
- Generated after rebuild: `docs/tracks/<track-slug>/index.html`
- Generated after rebuild: `docs/sources/index.html`
- Generated after rebuild: `docs/sources/<source-slug>/index.html`

## Current Baseline

- IA V2 Batch 1 is remote-confirmed: push run `25009309491`.
- IA V2 Batch 2 is locally complete: `/daily/`, `/sources/`, source detail pages, active sources on track pages, homepage recent archives capped at 8.
- IA V2 Batch 3 is remote-confirmed: push run `25035969439`, status `completed`, conclusion `success`, URL `https://github.com/wsysgz/VS_AI/actions/runs/25035969439`.
- Current homepage section order is roughly: `今日判断`, comparison, `赛道`, `来源`, `关键主线`, `重点信号`, `检索`, `最近归档`.
- Current track detail order is: hero, `活跃来源`, `最近日报`, `重点信号`.
- Current source detail order is: hero, `覆盖赛道`, `最近日报`, `重点信号`.

## Task 1: Add Homepage Guide Tests

**Files:**
- Modify: `tests/test_pages_builder.py`
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Write the failing test**

Add this test near the existing IA V2 Pages tests in `tests/test_pages_builder.py`, after `test_build_pages_site_generates_daily_index_and_homepage_chip`:

```python
def test_build_pages_site_homepage_prioritizes_workbench_tracks_and_sources(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI", publication_mode="reviewed")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    workbench_html = index_html.split('<section class="workbench">', 1)[1].split("</section>", 1)[0]

    assert "今日判断" in workbench_html
    assert 'class="guide-actions"' in workbench_html
    assert 'href="./tracks/"' in workbench_html
    assert 'href="./sources/"' in workbench_html
    assert workbench_html.index('class="guide-actions"') < workbench_html.index('href="./daily/"')
    assert workbench_html.index('class="guide-actions"') < workbench_html.index('href="./weekly/"')
    assert workbench_html.index('class="guide-actions"') < workbench_html.index('href="./special/"')
```

Add this companion assertion so the homepage does not promote daily/weekly/special as primary content sections:

```python
def test_build_pages_site_homepage_keeps_daily_weekly_special_secondary(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI", publication_mode="reviewed")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert '<a class="chip" href="./daily/">日报</a>' in index_html
    assert '<a class="chip" href="./weekly/">周报</a>' in index_html
    assert '<a class="chip" href="./special/">专题</a>' in index_html
    assert '<h2 class="section-title">日报</h2>' not in index_html
    assert '<h2 class="section-title">周报</h2>' not in index_html
    assert '<h2 class="section-title">专题</h2>' not in index_html
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_homepage_prioritizes_workbench_tracks_and_sources tests/test_pages_builder.py::test_build_pages_site_homepage_keeps_daily_weekly_special_secondary -q
```

Expected: the first test FAILS because `guide-actions` does not exist yet. The second test may PASS on the current baseline; keep it because it protects the user's decision that `日报 / 周报 / 专题` stay secondary.

## Task 2: Implement Homepage Workbench Guide

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [ ] **Step 1: Add guide action styles**

In `_base_css()` in `src/auto_report/outputs/pages_builder.py`, add these styles near the existing `.meta-row` / `.chip` styles:

```css
.guide-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 16px 0 6px;
}
.guide-action {
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  display: inline-flex;
  font-weight: 700;
  min-height: 40px;
  padding: 10px 14px;
  text-decoration: none;
}
.guide-action.primary {
  background: var(--text);
  border-color: var(--text);
  color: #fff;
}
.guide-action:focus,
.guide-action:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.guide-action.primary:focus,
.guide-action.primary:hover {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
```

Inside the existing mobile media blocks, keep the buttons compact:

```css
  .guide-actions { gap: 8px; }
  .guide-action {
    flex: 1 1 120px;
    justify-content: center;
    min-height: 38px;
    padding: 9px 12px;
  }
```

- [ ] **Step 2: Add the workbench guide actions**

In `_build_homepage()`, insert the guide action row inside the left workbench panel, after the executive summary list and before the existing `<div class="meta-row">`:

```python
        <div class="guide-actions" aria-label="工作台导读">
          <a class="guide-action primary" href="./tracks/">赛道</a>
          <a class="guide-action primary" href="./sources/">来源</a>
          <a class="guide-action" href="#top-signals">重点信号</a>
        </div>
```

Give the homepage `重点信号` section an anchor so the third guide action has a stable target:

```python
    <section class="section" id="top-signals">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(report["top_signals"], link_prefix="./")}
      </div>
    </section>
```

Keep the existing chip row, including `归档检索`, `日报`, `周报`, and `专题`, below the guide actions. This preserves secondary access while making `赛道 / 来源` the primary homepage route.

- [ ] **Step 3: Run the homepage guide tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_homepage_prioritizes_workbench_tracks_and_sources tests/test_pages_builder.py::test_build_pages_site_homepage_keeps_daily_weekly_special_secondary -q
```

Expected: PASS.

## Task 3: Add Track/Source Detail Ordering Tests

**Files:**
- Modify: `tests/test_pages_builder.py`
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Write the failing ordering tests**

Add these tests near `test_build_pages_site_generates_track_detail_pages` and `test_build_pages_site_generates_source_detail_pages`:

```python
def test_build_pages_site_track_detail_prioritizes_signals_before_supporting_sections(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    track_html = (tmp_path / "docs" / "tracks" / "ai-llm-agent" / "index.html").read_text(encoding="utf-8")

    signals = track_html.index('<h2 class="section-title">重点信号</h2>')
    active_sources = track_html.index('<h2 class="section-title">活跃来源</h2>')
    recent_daily = track_html.index('<h2 class="section-title">最近日报</h2>')

    assert signals < active_sources
    assert signals < recent_daily
```

```python
def test_build_pages_site_source_detail_prioritizes_signals_before_supporting_sections(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    electronics = _sample_payload("2026-04-10", "ai-x-electronics", "Renesas")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", electronics)

    build_pages_site(tmp_path)

    source_html = next((tmp_path / "docs" / "sources").glob("*/index.html")).read_text(encoding="utf-8")

    signals = source_html.index('<h2 class="section-title">重点信号</h2>')
    covered_tracks = source_html.index('<h2 class="section-title">覆盖赛道</h2>')
    recent_daily = source_html.index('<h2 class="section-title">最近日报</h2>')

    assert signals < covered_tracks
    assert signals < recent_daily
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_track_detail_prioritizes_signals_before_supporting_sections tests/test_pages_builder.py::test_build_pages_site_source_detail_prioritizes_signals_before_supporting_sections -q
```

Expected: FAIL because both templates currently render `重点信号` after `最近日报`.

## Task 4: Reorder Track/Source Detail Pages

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Test: `tests/test_pages_builder.py`

- [ ] **Step 1: Reorder the track detail template**

In `_build_track_page()`, keep the hero unchanged, then order the body sections as `重点信号`, `活跃来源`, `最近日报`:

```python
    <section class="section" id="top-signals">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(track_signals, link_prefix="../../")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">活跃来源</h2>
      <div class="archive-grid">
        {_source_summary_cards(track_sources, link_prefix="../../")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">最近日报</h2>
      <div class="archive-grid">
        {_archive_cards(track_reports[:8], link_prefix="../../")}
      </div>
    </section>
```

- [ ] **Step 2: Reorder the source detail template**

In `_build_source_page()`, keep the hero unchanged, then order the body sections as `重点信号`, `覆盖赛道`, `最近日报`:

```python
    <section class="section" id="top-signals">
      <h2 class="section-title">重点信号</h2>
      <div class="signal-grid">
        {_signal_cards(source_signals, link_prefix="../../")}
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">覆盖赛道</h2>
      <div class="archive-meta">{track_tags}</div>
    </section>

    <section class="section">
      <h2 class="section-title">最近日报</h2>
      <div class="archive-grid">
        {_archive_cards(source_reports[:8], link_prefix="../../")}
      </div>
    </section>
```

- [ ] **Step 3: Run the detail ordering tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_track_detail_prioritizes_signals_before_supporting_sections tests/test_pages_builder.py::test_build_pages_site_source_detail_prioritizes_signals_before_supporting_sections -q
```

Expected: PASS.

- [ ] **Step 4: Run the existing detail page tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py::test_build_pages_site_generates_track_detail_pages tests/test_pages_builder.py::test_build_pages_site_generates_source_detail_pages tests/test_pages_builder.py::test_build_pages_site_track_pages_surface_active_sources -q
```

Expected: PASS. Existing section presence and source cross-links remain intact.

## Task 5: Refresh Project Docs For IA V2 Closeout

**Files:**
- Modify: `V1升级方案.md`
- Modify: `交接备忘录.md`
- Modify: `AI对接手册.md`

- [ ] **Step 1: Confirm stale status text exists**

Run:

```powershell
rg -n "第三批|第四批|25035969439|最终收口|前面没完成的尾项|当前推进第三批|第三批正在推进" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected before edits: docs mention Batch 3 as the active stage and do not consistently mention Batch 3 remote success or Batch 4 final closeout.

- [ ] **Step 2: Update `V1升级方案.md`**

Replace the IA V2 status bullets around the current third-batch line with:

```md
- [x] 公开站 IA V2 第三批已完成并通过远端发布级确认：赛道/来源列表页检索与移动端导航/卡片压缩体验已落地；push run `25035969439` 已成功：`https://github.com/wsysgz/VS_AI/actions/runs/25035969439`
- [ ] 公开站 IA V2 第四批（最终收口）：首页工作台导读链路收敛为 `今日判断 -> 赛道 / 来源`，赛道/来源详情页优先呈现 `重点信号`，`日报 / 周报 / 专题` 只保留为次级入口
```

In the roadmap order section, replace the public-site line with:

```md
4. **公开站整理 / 优化（IA V2 第四批最终收口）**
   - 第一批、第二批、第三批均已完成；第三批远端发布级确认 run `25035969439` 成功
   - 第四批只做导读链路和详情页优先级收口，不新增页面类型
   - 第四批完成后切回前面没完成的尾项
```

- [ ] **Step 3: Update `交接备忘录.md`**

Update the top short-status bullets so they read:

```md
- 当前主线：`公开站 IA V2 第一批、第二批、第三批已完成；第三批远端发布级确认 run 25035969439 成功；当前执行第四批最终收口`
- 当前新增收口：公开站 IA V2 第四批已定范围：工作台导读链路收敛为 `今日判断 -> 赛道 / 来源`，赛道/来源详情页以 `重点信号` 为首要动作，`日报 / 周报 / 专题` 只保留为次级入口
```

Update the “下一步” or “如果下一位只剩 3 分钟” section with:

```md
1. 先按 `docs/superpowers/plans/2026-04-28-public-site-ia-v2-batch-4.md` 执行公开站最终收口
2. 本地验证和 Pages 重建通过后，再切回前面没完成的尾项
3. 当前明确尾项仍以 `renesas-blog` blocked（403）观察为主，不在 IA V2 第四批内扩源
```

- [ ] **Step 4: Update `AI对接手册.md`**

Update `60 秒接管`, `当前项目进度`, and `默认优先顺序` sections so they contain:

```md
- 当前主线优先级：`公开站 IA V2 第一批、第二批、第三批已完成；第三批远端发布级确认 run 25035969439 成功；当前执行第四批最终收口`
- 第四批范围：`首页工作台导读链路：今日判断 -> 赛道 / 来源；赛道/来源详情页：重点信号优先；日报 / 周报 / 专题：只保留次级入口`
- 第四批完成后：`切回前面没完成的尾项，优先检查 renesas-blog blocked（403）和持续治理记录`
```

- [ ] **Step 5: Verify doc wording**

Run:

```powershell
rg -n "25035969439|第四批|最终收口|前面没完成的尾项|重点信号优先|只保留为次级入口" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected: matches in all three docs.

Run:

```powershell
rg -n "第三批正在推进|当前推进第三批|继续 IA V2 第三批|当前第三批" V1升级方案.md 交接备忘录.md AI对接手册.md
```

Expected: no matches.

## Task 6: Rebuild Pages And Verify Locally

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`
- Modify: `tests/test_pages_builder.py`
- Modify: `V1升级方案.md`
- Modify: `交接备忘录.md`
- Modify: `AI对接手册.md`
- Generated: `docs/`

- [ ] **Step 1: Run Pages-focused tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_pages_builder.py -q
```

Expected: PASS.

- [ ] **Step 2: Rebuild the public site**

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

- [ ] **Step 3: Run full local tests**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Run workflow guard for the final closeout checkpoint**

Run:

```powershell
$env:PYTHONPATH='src'
pwsh ./scripts/check-workflows.ps1 -Profile full
```

Expected: PASS for workflow validation profiles.

- [ ] **Step 5: Preview the changed public pages**

Start or reuse the local preview server on port `8765`. If no server is running:

```powershell
python -m http.server 8765 -d docs
```

Open these URLs:

```text
http://127.0.0.1:8765/
http://127.0.0.1:8765/tracks/
http://127.0.0.1:8765/sources/
http://127.0.0.1:8765/tracks/ai-llm-agent/
```

Verify:

- Homepage first screen reads as `今日判断` with direct `赛道` and `来源` actions.
- `日报 / 周报 / 专题` remain reachable but do not become homepage primary sections.
- Track detail page shows `重点信号` before `活跃来源` and `最近日报`.
- Source detail page shows `重点信号` before `覆盖赛道` and `最近日报`.
- Mobile width keeps guide buttons and cards readable without text overlap.

## Task 7: Review And Handoff

**Files:**
- Review: `git diff -- src/auto_report/outputs/pages_builder.py tests/test_pages_builder.py V1升级方案.md 交接备忘录.md AI对接手册.md docs`

- [ ] **Step 1: Review the focused diff**

Run:

```powershell
git diff -- src/auto_report/outputs/pages_builder.py tests/test_pages_builder.py V1升级方案.md 交接备忘录.md AI对接手册.md docs
```

Expected: diff contains only IA V2 Batch 4 homepage guide, detail page ordering, generated Pages updates, and doc status refreshes.

- [ ] **Step 2: Check worktree status**

Run:

```powershell
git status --short
```

Expected: only the files listed in this plan are modified or generated.

- [ ] **Step 3: Commit after verification**

After tests and rebuild pass, commit the batch:

```powershell
git add src/auto_report/outputs/pages_builder.py tests/test_pages_builder.py V1升级方案.md 交接备忘录.md AI对接手册.md docs
git commit -m "feat: finish public site ia v2 batch 4"
```

Expected: one focused commit that closes public-site IA V2 Batch 4.

- [ ] **Step 4: Decide on remote confirmation**

Because this is a public-site IA final closeout, push only after local verification is clean:

```powershell
git push
```

Expected: GitHub Actions starts a push run for `Collect And Report`. Record the run ID and URL in the final handoff. Do not front-watch continuously unless a later task depends on it.

## Self-Review Checklist

- Spec coverage: homepage guide route, secondary `日报 / 周报 / 专题`, track/source `重点信号` priority, docs closeout, and return-to-tail handoff all have tasks.
- Placeholder scan: no open-ended implementation steps are left without code snippets, commands, or expected results.
- Type consistency: all tests use existing helpers `_sample_payload`, `_write_report_set`, and `build_pages_site`; all implementation changes stay inside existing builder functions.
- Scope control: no new page type, schema, package, provider, workflow, or service is introduced.
