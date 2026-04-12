from pathlib import Path

import pytest

from auto_report.workflow_guard import build_workflow_check_commands, run_workflow_checks


def test_build_workflow_check_commands_runs_actionlint_before_act():
    commands = build_workflow_check_commands(Path("D:/GitHub/auto"))

    assert commands[0][0] == "actionlint"
    assert commands[1][0] == "act"
    assert "--validate" in commands[1]
    assert commands[1][-1].endswith("collect-report.yml")


def test_build_workflow_check_commands_supports_daily_profile():
    commands = build_workflow_check_commands(Path("D:/GitHub/auto"), profile="daily")

    validated = [command[-1].replace("\\", "/") for command in commands[1:]]

    assert validated == [
        "D:/GitHub/auto/.github/workflows/collect-report.yml",
        "D:/GitHub/auto/.github/workflows/delivery-canary.yml",
    ]


def test_build_workflow_check_commands_supports_recovery_profile():
    commands = build_workflow_check_commands(Path("D:/GitHub/auto"), profile="recovery")

    validated = [command[-1].replace("\\", "/") for command in commands[1:]]

    assert validated == [
        "D:/GitHub/auto/.github/workflows/backfill-report.yml",
        "D:/GitHub/auto/.github/workflows/compensate-report.yml",
    ]


def test_build_workflow_check_commands_supports_full_profile():
    commands = build_workflow_check_commands(Path("D:/GitHub/auto"), profile="full")

    validated = [Path(command[-1]).name for command in commands[1:]]

    assert validated == [
        "backfill-report.yml",
        "collect-report.yml",
        "compensate-report.yml",
        "delivery-canary.yml",
    ]


def test_build_workflow_check_commands_rejects_unknown_profile():
    with pytest.raises(ValueError, match="Unknown workflow validation profile: fast"):
        build_workflow_check_commands(Path("D:/GitHub/auto"), profile="fast")


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


def test_run_workflow_checks_executes_requested_profile(monkeypatch):
    calls: list[list[str]] = []

    monkeypatch.setattr("auto_report.workflow_guard.shutil.which", lambda name: f"C:/tools/{name}.exe")

    def fake_runner(command, cwd, check):
        calls.append(command)

    run_workflow_checks(Path("D:/GitHub/auto"), profile="recovery", runner=fake_runner)

    assert [Path(command[-1]).name for command in calls[1:]] == [
        "backfill-report.yml",
        "compensate-report.yml",
    ]
