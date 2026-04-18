# Discovery/Search Helper Artifact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone keyword-driven discovery/search helper that uses MiniMax-M2.7 to produce structured candidate artifacts for source exploration.

**Architecture:** Reuse the existing CLI -> app -> artifact pattern already used by source governance and review queue outputs. Keep the first batch isolated from the main report flow and output only JSON/Markdown artifacts.

**Tech Stack:** Python, existing `call_llm(...)`, argparse, JSON/Markdown output, pytest.

---

## File Map

- Create: `D:\GitHub\auto\config\source_discovery\keywords.txt`
- Create: `D:\GitHub\auto\src\auto_report\pipeline\discovery_search.py`
- Modify: `D:\GitHub\auto\src\auto_report\app.py`
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
- Test: `D:\GitHub\auto\tests\test_cli_smoke.py`
- Create: `D:\GitHub\auto\tests\test_discovery_search.py`

### Task 1: Expose the new CLI command

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\cli.py`
- Test: `D:\GitHub\auto\tests\test_cli_smoke.py`

- [ ] **Step 1: Write the failing parser test**

Add assertions like:

```python
assert "build-discovery-search" in choices

args = parser.parse_args(["build-discovery-search", "--keywords", "config/source_discovery/keywords.txt"])
assert args.command == "build-discovery-search"
assert args.keywords == "config/source_discovery/keywords.txt"
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_cli_smoke.py -q
```

Expected: FAIL because the command does not exist yet.

- [ ] **Step 3: Add the command**

In `D:\GitHub\auto\src\auto_report\cli.py`:

- add `build-discovery-search`
- require `--keywords`
- route it to a new app command

- [ ] **Step 4: Re-run the test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_cli_smoke.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auto_report/cli.py tests/test_cli_smoke.py
git commit -m "feat: add discovery search cli entrypoint"
```

### Task 2: Implement keyword parsing and artifact generation

**Files:**
- Create: `D:\GitHub\auto\src\auto_report\pipeline\discovery_search.py`
- Create: `D:\GitHub\auto\tests\test_discovery_search.py`
- Create: `D:\GitHub\auto\config\source_discovery\keywords.txt`

- [ ] **Step 1: Write the failing tests**

Add tests for:

```python
keywords = load_keywords(path)
assert keywords == ["Anthropic news", "Jetson edge AI"]

payload = parse_discovery_response(raw_json_text)
assert payload["items"][0]["keyword"] == "Anthropic news"
assert payload["items"][0]["candidates"][0]["classification"] == "official-site"
```

Also test artifact writing:

```python
output_path = build_discovery_search_artifact(tmp_path, keywords_path)
assert output_path.name == "discovery-search.json"
assert (tmp_path / "out" / "discovery-search" / "discovery-search.md").exists()
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_discovery_search.py -q
```

Expected: FAIL because the module does not exist yet.

- [ ] **Step 3: Implement the minimal module**

In `D:\GitHub\auto\src\auto_report\pipeline\discovery_search.py`, add:

- `load_keywords(path: Path) -> list[str]`
- `build_discovery_prompt(keyword: str) -> str`
- `parse_discovery_response(text: str) -> dict[str, object]`
- `build_discovery_search_artifact(root_dir: Path, keywords_path: Path) -> Path`

Artifact behavior:

- JSON at `out/discovery-search/discovery-search.json`
- Markdown at `out/discovery-search/discovery-search.md`

Model call:

```python
call_llm(prompt, stage="search")
```

- [ ] **Step 4: Re-run the test**

Run:

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_discovery_search.py -q
```

Expected: PASS.

- [ ] **Step 5: Add starter keywords file**

Create `D:\GitHub\auto\config\source_discovery\keywords.txt` with a small starter set such as:

```text
# ai-llm-agent
Anthropic news
OpenAI safety updates

# ai-x-electronics
Jetson edge AI
Qualcomm on-device AI
```

- [ ] **Step 6: Commit**

```bash
git add src/auto_report/pipeline/discovery_search.py tests/test_discovery_search.py config/source_discovery/keywords.txt
git commit -m "feat: add discovery search artifact builder"
```

### Task 3: Wire the app entrypoint

**Files:**
- Modify: `D:\GitHub\auto\src\auto_report\app.py`

- [ ] **Step 1: Add the app command**

Implement:

```python
def cmd_build_discovery_search(root_dir: Path, keywords_path: str) -> Path:
    from auto_report.pipeline.discovery_search import build_discovery_search_artifact
    return build_discovery_search_artifact(root_dir, Path(keywords_path))
```

- [ ] **Step 2: Verify command wiring through CLI**

Run:

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-discovery-search --keywords config/source_discovery/keywords.txt
```

Expected: JSON and Markdown artifacts are written under `out/discovery-search/`.

- [ ] **Step 3: Commit**

```bash
git add src/auto_report/app.py
git commit -m "feat: wire discovery search app command"
```

### Task 4: Final verification

**Files:**
- Verify only

- [ ] **Step 1: Run focused tests**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests/test_cli_smoke.py tests/test_discovery_search.py tests/test_llm_client.py tests/test_settings.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the helper command**

```powershell
$env:PYTHONPATH='src'
python -m auto_report.cli build-discovery-search --keywords config/source_discovery/keywords.txt
```

Expected:

- `out/discovery-search/discovery-search.json`
- `out/discovery-search/discovery-search.md`

- [ ] **Step 3: Run full suite**

```powershell
$env:PYTHONPATH='src'
python -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: Commit verification checkpoint**

```bash
git status --short
git commit --allow-empty -m "chore: verify discovery search helper"
```
