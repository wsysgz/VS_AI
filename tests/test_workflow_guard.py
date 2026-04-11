from pathlib import Path

import pytest

from auto_report.workflow_guard import build_workflow_check_commands, run_workflow_checks


def test_build_workflow_check_commands_runs_actionlint_before_act():
    commands = build_workflow_check_commands(Path("D:/GitHub/auto"))

    assert commands[0][0] == "actionlint"
    assert commands[1][0] == "act"
    assert "--validate" in commands[1]


def test_run_workflow_checks_fails_clearly_when_tools_missing(monkeypatch):
    monkeypatch.setattr("auto_report.workflow_guard.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="Missing required workflow tools: actionlint, act"):
        run_workflow_checks(Path("D:/GitHub/auto"))


def test_run_workflow_checks_executes_commands_in_order(monkeypatch):
    calls: list[list[str]] = []

    monkeypatch.setattr("auto_report.workflow_guard.shutil.which", lambda name: f"C:/tools/{name}.exe")

    def fake_runner(command, cwd, check):
        calls.append(command)

    run_workflow_checks(Path("D:/GitHub/auto"), runner=fake_runner)

    assert calls[0][0] == "actionlint"
    assert calls[1][0] == "act"
