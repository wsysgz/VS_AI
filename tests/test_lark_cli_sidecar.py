from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from auto_report.integrations.lark_cli import SIDE_CAR_STATE_PATH, sync_feishu_workspace
from auto_report.settings import load_settings


def _write_reviewed_report(root_dir: Path) -> None:
    reports_dir = root_dir / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "latest-summary-reviewed.md").write_text(
        "# VS_AI reviewed report\n\n- key change\n- key risk\n",
        encoding="utf-8",
    )


def _write_governance_artifact(root_dir: Path) -> None:
    artifact_path = root_dir / "out" / "source-governance" / "source-governance.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-18T14:00:00+08:00",
                "source_governance": {
                    "summary": {
                        "manual_review_count": 1,
                        "rsshub_candidate_count": 2,
                        "changedetection_candidate_count": 3,
                        "replacement_candidate_count": 4,
                    },
                    "priority_queue": [
                        {
                            "source_id": "anthropic-news",
                            "candidate_kind": "changedetection_watch",
                            "priority_label": "high",
                            "priority_score": 90,
                            "next_action": "Create a changedetection watch.",
                            "replacement_target": "rsshub-or-feed",
                            "url": "https://www.anthropic.com/news",
                        },
                        {
                            "source_id": "nxp-edge-ai",
                            "candidate_kind": "manual_replace",
                            "priority_label": "high",
                            "priority_score": 80,
                            "next_action": "Review this source and replace it.",
                            "replacement_target": "stable-nxp-listing",
                            "url": "https://www.nxp.com/company/about-nxp/smarter-world-blog",
                        },
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _settings_for(tmp_path: Path, monkeypatch) -> object:
    shutil.copytree(Path.cwd() / "config", tmp_path / "config")
    monkeypatch.setenv("LARK_CLI_PATH", "D:\\AI\\Feishu\\feushu_cli\\lark-cli.exe")
    monkeypatch.setenv("LARK_CLI_PROFILE", "vs_ai")
    return load_settings(tmp_path)


def test_sync_feishu_workspace_creates_resources_and_persists_state(tmp_path, monkeypatch):
    _write_reviewed_report(tmp_path)
    _write_governance_artifact(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "docs +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"document": {"document_id": "doc_1", "url": "https://doc/1"}}), stderr="")
        if "sheets +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"spreadsheet": {"spreadsheet_token": "sheet_1", "url": "https://sheet/1"}}), stderr="")
        if "sheets +info" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"sheets": [{"sheet_id": "sheetA"}]}), stderr="")
        if "task +tasklist-create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"tasklist": {"guid": "tl_1", "url": "https://tasklist/1"}}), stderr="")
        if "task +create" in joined:
            source_id = "anthropic-news" if "anthropic-news" in joined else "nxp-edge-ai"
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": f"task_{source_id}", "url": f"https://task/{source_id}"}}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = sync_feishu_workspace(tmp_path, settings, publication_mode="reviewed")

    assert result["report_doc"]["doc_token"] == "doc_1"
    assert result["governance_sheet"]["spreadsheet_token"] == "sheet_1"
    assert result["governance_sheet"]["sheet_id"] == "sheetA"
    assert result["governance_tasks"]["tasklist_id"] == "tl_1"
    assert set(result["governance_tasks"]["tasks_by_source"]) == {"anthropic-news", "nxp-edge-ai"}
    assert any("docs +create" in " ".join(command) for command in calls)
    assert any("sheets +create" in " ".join(command) for command in calls)
    assert any("task +tasklist-create" in " ".join(command) for command in calls)

    state = json.loads((tmp_path / SIDE_CAR_STATE_PATH).read_text(encoding="utf-8"))
    assert state["report_doc"]["doc_token"] == "doc_1"
    assert state["governance_sheet"]["sheet_id"] == "sheetA"
    assert state["governance_tasks"]["tasklist_id"] == "tl_1"


def test_sync_feishu_workspace_updates_existing_resources(tmp_path, monkeypatch):
    _write_reviewed_report(tmp_path)
    _write_governance_artifact(tmp_path)
    settings = _settings_for(tmp_path, monkeypatch)
    state_path = tmp_path / SIDE_CAR_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "report_doc": {"doc_token": "doc_existing", "url": "https://doc/existing"},
                "governance_sheet": {
                    "spreadsheet_token": "sheet_existing",
                    "sheet_id": "sheetABC",
                    "url": "https://sheet/existing",
                },
                "governance_tasks": {
                    "tasklist_id": "tl_existing",
                    "url": "https://tasklist/existing",
                    "tasks_by_source": {
                        "anthropic-news": {"task_id": "task_existing", "url": "https://task/existing"}
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check, cwd=None, encoding=None, errors=None):
        calls.append(command)
        joined = " ".join(command)
        if "docs +update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"document": {"document_id": "doc_existing", "url": "https://doc/existing"}}), stderr="")
        if "sheets +write" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"updatedRange": "sheetABC!A1:G3"}), stderr="")
        if "task +update" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": "task_existing", "url": "https://task/existing"}}), stderr="")
        if "task +create" in joined:
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"task": {"guid": "task_nxp-edge-ai", "url": "https://task/nxp-edge-ai"}}), stderr="")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr("auto_report.integrations.lark_cli.subprocess.run", fake_run)

    result = sync_feishu_workspace(tmp_path, settings, publication_mode="reviewed")

    assert result["report_doc"]["doc_token"] == "doc_existing"
    assert result["governance_sheet"]["sheet_id"] == "sheetABC"
    assert result["governance_tasks"]["tasks_by_source"]["anthropic-news"]["task_id"] == "task_existing"
    assert result["governance_tasks"]["tasks_by_source"]["nxp-edge-ai"]["task_id"] == "task_nxp-edge-ai"
    assert any("docs +update" in " ".join(command) for command in calls)
    assert any("sheets +write" in " ".join(command) for command in calls)
    assert any("task +update" in " ".join(command) for command in calls)
