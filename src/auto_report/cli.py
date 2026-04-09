from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once", help="Collect, analyze, render, and archive reports once")
    subparsers.add_parser("backfill", help="Reserved entrypoint for historical reruns")
    subparsers.add_parser("render-report", help="Render reports from current state without recollecting")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root_dir = Path.cwd()

    if args.command == "run-once":
        from auto_report.app import run_once

        run_once(root_dir)
        return 0

    if args.command == "render-report":
        from auto_report.app import render_reports

        render_reports(root_dir)
        return 0

    if args.command == "backfill":
        parser.error("The 'backfill' command is reserved for the next implementation batch.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
