# Public Site Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将公开站首页从展示型阅读页改成中文优先的情报工作台，并保留当前 GitHub Pages 静态发布链路。

**Architecture:** 继续由 `src/auto_report/outputs/pages_builder.py` 读取报告 JSON 并生成 `docs/`。本轮只做首页/二级页文案、布局、`comparison_brief` 展示和样式重构，不引入新框架。

**Tech Stack:** Python 静态生成、现有 `pytest` 页面生成测试、GitHub Pages `docs/` 输出、Playwright/Edge 截图验收。

---

### Task 1: 测试公开站工作台行为

**Files:**
- Modify: `tests/test_pages_builder.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert:
- 首页出现中文工作台文案。
- 首页在报告含 `comparison_brief` 时展示国内外对比。
- 老报告没有 `comparison_brief` 时仍可构建，且不展示空模块。

- [ ] **Step 2: Run targeted tests to verify failure**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_pages_builder.py -q`
Expected: at least one failure for missing workbench/comparison output.

### Task 2: 实现中文工作台首页

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Normalize comparison brief**

Add a small normalizer that reads `comparison_brief.cn_highlights`, `intl_highlights`, `head_to_head`, `gaps`, and `watchpoints` with safe defaults.

- [ ] **Step 2: Render homepage workbench**

Replace the oversized hero with a compact workbench:
- 顶部中文导航
- 今日判断
- 关键指标
- 国内外对比预览
- 重点信号
- 检索
- 最近归档

- [ ] **Step 3: Keep old reports safe**

When `comparison_brief` is missing, skip the comparison section.

### Task 3: 中文化二级页面和样式

**Files:**
- Modify: `src/auto_report/outputs/pages_builder.py`

- [ ] **Step 1: Update navigation labels**

Use `首页`、`归档`、`周报`、`专题`、`订阅`、`仓库` on generated pages.

- [ ] **Step 2: Tune visual system**

Reduce hero scale, use workbench-style grids, keep stable mobile layout, and keep card radius restrained.

### Task 4: Verify and inspect

**Files:**
- Generated: `docs/index.html`
- Generated: `docs/archives/`
- Generated: `docs/weekly/`
- Generated: `docs/special/`

- [ ] **Step 1: Run page tests**

Run: `$env:PYTHONPATH='src'; python -m pytest tests/test_pages_builder.py -q`
Expected: all page builder tests pass.

- [ ] **Step 2: Build pages locally**

Run: `$env:PYTHONPATH='src'; python -m auto_report.cli build-pages`
Expected: command exits 0 and writes `docs/index.html`.

- [ ] **Step 3: Capture screenshots**

Run Edge/Playwright screenshots for desktop and mobile against local `docs/index.html` or a local static server.
Expected: no text overlap, mobile nav readable, first screen shows workbench content.
