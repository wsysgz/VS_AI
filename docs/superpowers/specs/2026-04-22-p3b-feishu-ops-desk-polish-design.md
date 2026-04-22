# P3-B Feishu Ops Desk Polish Design

**Date:** 2026-04-22
**Workspace:** `D:\GitHub\auto`
**Depends on:** `D:\GitHub\auto\docs\superpowers\specs\2026-04-22-p3b-feishu-ops-desk-design.md`

## Goal

Define the second `P3-B` design pass that improves the existing Feishu ops desk from “usable” to “comfortable for daily operation” by focusing on:

1. clearer Chinese naming,
2. dashboard-first visual hierarchy,
3. button-first navigation,
4. lighter operator typing burden,
5. selective low-risk automation that supports operations without taking over repo execution.

## Scope

This batch is a UI/UX and operations-surface optimization batch for the existing first implementation.

In scope:

- Chinese dashboard title and card copy
- better view naming
- better field ordering
- reducing free-text input where possible
- dashboard module polish
- light automation recommendations and first-batch inclusion rules

Out of scope:

- replacing the existing four-table data model
- allowing direct source-config edits from Feishu
- allowing Feishu to trigger repo apply / publish / workflow execution
- moving to Feishu application mode as the main front-end
- reworking repo truth boundaries

## User Decisions Already Made

- The dashboard should stay `方案 B：标准运营台`
- The dashboard should be dashboard-first, not list-first
- The first page should answer “今天该点什么、该批什么、该看什么”
- Navigation should be grouped by business module
- Feishu should be optimized for clicking and selecting, not typing
- Chinese labels and a less text-heavy look are preferred

## Product Direction

### 1. Home Page Identity

The home page should stop looking like a generic base export and instead feel like a daily operator cockpit.

Recommended title:

- `VS_AI 今日运营台`

Recommended subtitle:

- `先看状态，再进入处理`

This gives the page a daily-use tone rather than a generic “dashboard” tone.

### 2. Home Page Layout

The chosen home structure should be:

#### Top row: four summary cards

- `飞书交付`
- `来源治理`
- `审批协作`
- `待应用变更`

Each summary card should contain:

- one status sentence
- two key metrics
- two action buttons

This keeps each card readable while still action-oriented.

#### Middle area: four business modules

Each module should correspond to one of the four tables and should expose:

- a short status sentence
- a few key counts
- a primary action button
- a secondary detail button

#### Bottom area: 今日操作建议

This should summarize:

- what to look at first
- what to approve next
- whether delivery verification is pending

The dashboard should guide attention instead of forcing the operator to interpret raw data.

## Naming Design

### 1. Dashboard Modules

Keep all module names in Chinese:

- `飞书交付`
- `来源治理`
- `审批协作`
- `待应用变更`

Do not use mixed English labels like:

- `Ops Desk`
- `Lead Review`
- `Delivery Audit`

on the landing page itself.

English table names may continue internally if needed for CLI compatibility, but user-facing labels should be Chinese-first.

### 2. View Names

#### Lead Review views

Rename to:

- `待审批`
- `已批准`
- `已延后`
- `最近更新`

#### Delivery Audit views

Rename to:

- `待验收`
- `最近交付`
- `发现回退`
- `已确认卡片`

#### Governance Main views

Rename to:

- `高优先级来源`
- `阻塞来源`
- `人工复核来源`
- `候选替换来源`

#### Candidate Updates views

Rename to:

- `待应用变更`
- `可应用`
- `有阻塞`
- `仅查看`

These names should reflect operator intention rather than technical table semantics.

## Field Order Design

### 1. Lead Review

Recommended visible order:

1. `标题`
2. `状态`
3. `备注`
4. `优先级`
5. `关键词`
6. `来源桶`
7. `更新时间`
8. `lead_key`

Rationale:

- title + status + note are the real working fields
- long machine keys should move to the far right

### 2. Delivery Audit

Recommended visible order:

1. `生成时间`
2. `发布轨`
3. `飞书状态`
4. `卡片已确认`
5. `发现回退`
6. `验收备注`
7. `风险等级`
8. `Feishu 消息 ID`
9. `Trace 链接`

Rationale:

- human validation fields should appear before technical trace fields

### 3. Governance Main

Recommended visible order:

1. `source_id`
2. `优先级`
3. `候选类型`
4. `下一步动作`
5. `替代目标`
6. `稳定层级`
7. `watch 策略`
8. `自动化准备`
9. `URL`
10. `更新时间`

### 4. Candidate Updates

Recommended visible order:

1. `source_id`
2. `变更摘要`
3. `变更类型`
4. `可应用`
5. `阻塞原因`
6. `校验模式`
7. `生成时间`
8. `update_key`

## Interaction Design

### 1. Button-First Principle

The user explicitly prefers clicking over typing.

So first-batch interaction should favor:

- action buttons on dashboard cards
- prebuilt views instead of manual filtering
- select / checkbox style fields instead of free-text entry

Typing should be limited mainly to notes.

### 2. Dashboard Buttons

Recommended primary / secondary buttons:

#### 飞书交付

- primary: `去验收`
- secondary: `看最近记录`

#### 来源治理

- primary: `看高优先级`
- secondary: `看阻塞来源`

#### 审批协作

- primary: `去审批`
- secondary: `看最近更新`

#### 待应用变更

- primary: `看待应用`
- secondary: `看阻塞原因`

### 3. Table Edit Burden

Reduce typing by using field types appropriately:

#### Lead Review

- `status` should become a selectable status field
- `note` remains free text

#### Delivery Audit

- `card_verified` should become checkbox / boolean-friendly
- `fallback_observed` should become checkbox / boolean-friendly
- `delivery_note` remains free text

This preserves the repo truth model while making Feishu interaction lighter.

## Visual Language

### 1. Overall Tone

The page should not feel like a plain text export.

Recommended tone:

- calm
- operator-focused
- compact but not crowded
- Chinese-first and status-first

### 2. Color Semantics

Use clear state colors:

- blue: primary action / normal entry state
- green: verified / healthy
- orange: pending / waiting
- red: blocked / risk
- neutral gray: informational / read-only

### 3. Card Structure

Each card should follow the same visual rhythm:

1. module title
2. one-line status sentence
3. two key metrics
4. two action buttons

This is a better operator pattern than dumping multiple text rows into each card.

## Automation Design

### 1. Recommended For First Batch

Only low-risk “supporting automation” should be included:

- status-based view grouping
- pending-count summaries on dashboard
- “待验收” view based on empty `card_verified`
- “发现回退” view based on `fallback_observed=true`
- “待审批” view based on `status=pending`

These are presentation and coordination aids, not execution controls.

### 2. Not Recommended Yet

Do not include in this polish batch:

- auto-apply source updates from Feishu
- auto-trigger GitHub workflows
- auto-publish reports
- auto-mutate repo config files from Feishu changes

That would break the chosen truth boundary and make the system much riskier.

## Reference Alignment

This polish direction aligns with official Feishu product patterns:

- multidimensional tables used as business-facing work surfaces
- dashboard-first summary for daily operations
- automation used mainly as coordination glue
- application-mode suitable as a later upgrade path, not a first-batch dependency

The core adaptation for this repo is:

- Feishu improves operator comfort
- repo JSON/config remains the ground truth

## Rollout Recommendation

### Phase P3-B.1

- Chinese view names
- field order cleanup
- dashboard copy cleanup
- dashboard button mapping

### Phase P3-B.2

- selectable status fields
- checkbox-style delivery verification fields
- low-risk view automation

### Phase P3-B.3

- visual polish pass
- better dashboard card hierarchy
- evaluate whether application-mode is worth the extra complexity

## Verification

Acceptance criteria for this polish batch:

1. the user can identify the right next action from the dashboard in under 30 seconds
2. the dashboard reads naturally in Chinese without requiring technical interpretation
3. the most common operator actions can be reached via saved views and buttons instead of manual filtering
4. only note fields require routine typing
5. no new automation bypasses repo truth or local verification rules
