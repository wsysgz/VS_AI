from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Callable


CommandRunner = Callable[..., object]
WORKFLOW_PROFILES = {
    "daily": [
        "collect-report.yml",
        "delivery-canary.yml",
    ],
    "recovery": [
        "backfill-report.yml",
        "compensate-report.yml",
    ],
    "full": [
        "backfill-report.yml",
        "collect-report.yml",
        "compensate-report.yml",
        "delivery-canary.yml",
    ],
}


def _resolve_profile(profile: str) -> list[str]:
    normalized = str(profile or "daily").strip().lower() or "daily"
    workflows = WORKFLOW_PROFILES.get(normalized)
    if workflows is None:
        raise ValueError(f"Unknown workflow validation profile: {profile}")
    return workflows


def build_workflow_check_commands(root_dir: Path, profile: str = "daily") -> list[list[str]]:
    workflow_dir = root_dir / ".github" / "workflows"
    commands: list[list[str]] = [["actionlint"]]
    for workflow_name in _resolve_profile(profile):
        workflow_path = workflow_dir / workflow_name
        commands.append(["act", "--validate", "-W", str(workflow_path)])
    return commands


def _missing_workflow_tools() -> list[str]:
    required = ("actionlint", "act")
    return [tool for tool in required if shutil.which(tool) is None]


def run_workflow_checks(
    root_dir: Path,
    profile: str = "daily",
    runner: CommandRunner | None = None,
) -> list[list[str]]:
    missing = _missing_workflow_tools()
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"Missing required workflow tools: {missing_text}")

    command_runner = runner or subprocess.run
    commands = build_workflow_check_commands(root_dir, profile=profile)
    for command in commands:
        command_runner(command, cwd=root_dir, check=True)
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(prog="workflow-guard")
    parser.add_argument("--root", default=".", help="Repository root to validate")
    parser.add_argument(
        "--profile",
        choices=sorted(WORKFLOW_PROFILES.keys()),
        default="daily",
        help="Workflow validation profile",
    )
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    commands = run_workflow_checks(root_dir, profile=args.profile)
    for command in commands:
        print(f"[workflow-guard] {' '.join(command)}")
    print("[workflow-guard] Workflow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
