from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once", help="Collect, analyze, render, and archive reports once")
    backfill_parser = subparsers.add_parser("backfill", help="Rerun the report pipeline for a specific target date")
    backfill_parser.add_argument("--target-date", default="", help="Target date in YYYY-MM-DD format, defaults to today")
    subparsers.add_parser("render-report", help="Render reports from current state without recollecting")

    # CI 专用命令 — Phase 0: 拆分为三个独立阶段供多 job workflow 使用
    subparsers.add_parser("collect-only", help="[CI] Collect + dedup + classify + score, save intermediate result")
    subparsers.add_parser("analyze-only", help="[CI] Run AI 3-stage pipeline on collected data")
    subparsers.add_parser("render-and-push", help="[CI] Render MD/JSON/HTML + push to all channels + archive")
    subparsers.add_parser("build-pages", help="[CI] Build GitHub Pages site (index + archives)")

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
        from auto_report.app import run_backfill

        target_date = getattr(args, "target_date", None) or ""
        run_backfill(root_dir, target_date=target_date)
        return 0

    # ===== CI 专用命令 =====
    if args.command == "collect-only":
        from auto_report.app import cmd_collect_only

        cmd_collect_only(root_dir)
        return 0

    if args.command == "analyze-only":
        from auto_report.app import cmd_analyze_only

        cmd_analyze_only(root_dir)
        return 0

    if args.command == "render-and-push":
        from auto_report.app import cmd_render_and_push

        cmd_render_and_push(root_dir)
        return 0

    if args.command == "build-pages":
        from auto_report.outputs.pages_builder import build_pages_site

        build_pages_site(root_dir)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
