from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Callable


CommandRunner = Callable[..., object]


def build_workflow_check_commands(root_dir: Path) -> list[list[str]]:
    workflow_path = root_dir / ".github" / "workflows" / "collect-report.yml"
    return [
        ["actionlint"],
        ["act", "--validate", "-W", str(workflow_path)],
    ]


def _missing_workflow_tools() -> list[str]:
    required = ("actionlint", "act")
    return [tool for tool in required if shutil.which(tool) is None]


def run_workflow_checks(root_dir: Path, runner: CommandRunner | None = None) -> list[list[str]]:
    missing = _missing_workflow_tools()
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"Missing required workflow tools: {missing_text}")

    command_runner = runner or subprocess.run
    commands = build_workflow_check_commands(root_dir)
    for command in commands:
        command_runner(command, cwd=root_dir, check=True)
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(prog="workflow-guard")
    parser.add_argument("--root", default=".", help="Repository root to validate")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    commands = run_workflow_checks(root_dir)
    for command in commands:
        print(f"[workflow-guard] {' '.join(command)}")
    print("[workflow-guard] Workflow checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
