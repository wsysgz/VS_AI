from __future__ import annotations

import argparse
from pathlib import Path


def _add_publication_mode_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--publication-mode",
        choices=("auto", "reviewed"),
        default="",
        help="Select publication track for this run; defaults to env PUBLICATION_MODE or auto",
    )


def _add_review_metadata_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reviewer", default="", help="Optional reviewer name for reviewed publication mode")
    parser.add_argument("--review-note", default="", help="Optional review note for reviewed publication mode")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auto-report")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_once_parser = subparsers.add_parser("run-once", help="Collect, analyze, render, and archive reports once")
    _add_publication_mode_argument(run_once_parser)
    _add_review_metadata_arguments(run_once_parser)
    backfill_parser = subparsers.add_parser("backfill", help="Rerun the report pipeline for a specific target date")
    backfill_parser.add_argument("--target-date", default="", help="Target date in YYYY-MM-DD format, defaults to today")
    _add_publication_mode_argument(backfill_parser)
    _add_review_metadata_arguments(backfill_parser)
    render_report_parser = subparsers.add_parser("render-report", help="Render reports from current state without recollecting")
    _add_publication_mode_argument(render_report_parser)
    _add_review_metadata_arguments(render_report_parser)
    diagnose_parser = subparsers.add_parser("diagnose-delivery", help="Inspect or send delivery test messages")
    diagnose_parser.add_argument(
        "--mode",
        choices=("canary", "full-report"),
        default="canary",
        help="Delivery diagnostic mode",
    )
    diagnose_parser.add_argument("--send", action="store_true", help="Actually send test messages to configured channels")
    diagnose_parser.add_argument(
        "--channels",
        default="",
        help="Optional comma-separated channels to test (feishu,pushplus,telegram)",
    )
    diagnose_parser.add_argument(
        "--require-feishu-card-success",
        action="store_true",
        help="Fail if Feishu delivery falls back to text instead of card_success",
    )

    # CI 专用命令 — Phase 0: 拆分为三个独立阶段供多 job workflow 使用
    subparsers.add_parser("collect-only", help="[CI] Collect + dedup + classify + score, save intermediate result")
    subparsers.add_parser("analyze-only", help="[CI] Run AI 3-stage pipeline on collected data")
    render_and_push_parser = subparsers.add_parser("render-and-push", help="[CI] Render MD/JSON/HTML + push to all channels + archive")
    _add_publication_mode_argument(render_and_push_parser)
    _add_review_metadata_arguments(render_and_push_parser)
    subparsers.add_parser("build-pages", help="[CI] Build GitHub Pages site (index + archives)")
    subparsers.add_parser("build-ops-dashboard", help="[CI] Build private ops dashboard artifact")
    subparsers.add_parser("build-source-governance", help="[CI] Build source governance artifact")
    subparsers.add_parser("build-review-queue", help="[CI] Build human review issue payloads from latest report")
    feishu_workspace_parser = subparsers.add_parser(
        "sync-feishu-workspace",
        help="[Ops] Publish latest report to Feishu Doc and sync governance sheet/tasks",
    )
    _add_publication_mode_argument(feishu_workspace_parser)
    subparsers.add_parser(
        "sync-feishu-ops-desk",
        help="[Ops] Sync the Feishu ops desk base/tables from repo truth",
    )
    subparsers.add_parser(
        "pull-feishu-ops-status",
        help="[Ops] Pull writable Feishu ops desk statuses back into repo JSON",
    )
    discovery_parser = subparsers.add_parser("build-discovery-search", help="[CI] Build keyword-driven discovery/search helper artifact")
    discovery_parser.add_argument("--keywords", required=True, help="Path to keyword list file")
    eval_parser = subparsers.add_parser("evaluate-prompts", help="[CI] Run offline prompt evaluation against a dataset")
    eval_parser.add_argument("--dataset", required=True, help="Path to offline prompt evaluation dataset JSON")
    apply_updates_parser = subparsers.add_parser(
        "apply-source-updates",
        help="[Ops] Apply safe approved source updates and rebuild governance artifacts",
    )
    apply_updates_parser.add_argument("--dry-run", action="store_true", help="Preview applyable updates without writing config files")
    subparsers.add_parser("run-watch-checks", help="[Ops] Run repo-local watch checks for active local watch entries")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root_dir = Path.cwd()

    if args.command == "run-once":
        from auto_report.app import run_once

        run_once(
            root_dir,
            publication_mode=getattr(args, "publication_mode", ""),
            reviewer=getattr(args, "reviewer", ""),
            review_note=getattr(args, "review_note", ""),
        )
        return 0

    if args.command == "render-report":
        from auto_report.app import render_reports

        render_reports(
            root_dir,
            publication_mode=getattr(args, "publication_mode", ""),
            reviewer=getattr(args, "reviewer", ""),
            review_note=getattr(args, "review_note", ""),
        )
        return 0

    if args.command == "backfill":
        from auto_report.app import run_backfill

        target_date = getattr(args, "target_date", None) or ""
        run_backfill(
            root_dir,
            target_date=target_date,
            publication_mode=getattr(args, "publication_mode", ""),
            reviewer=getattr(args, "reviewer", ""),
            review_note=getattr(args, "review_note", ""),
        )
        return 0

    if args.command == "diagnose-delivery":
        from auto_report.app import cmd_diagnose_delivery

        summary = cmd_diagnose_delivery(
            root_dir,
            send=getattr(args, "send", False),
            mode=getattr(args, "mode", "canary"),
            channels=getattr(args, "channels", ""),
            require_feishu_card_success=getattr(args, "require_feishu_card_success", False),
        )
        return 1 if summary["failed_channels"] else 0

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

        cmd_render_and_push(
            root_dir,
            publication_mode=getattr(args, "publication_mode", ""),
            reviewer=getattr(args, "reviewer", ""),
            review_note=getattr(args, "review_note", ""),
        )
        return 0

    if args.command == "build-pages":
        from auto_report.outputs.pages_builder import build_pages_site

        build_pages_site(root_dir)
        return 0

    if args.command == "build-ops-dashboard":
        from auto_report.outputs.ops_dashboard import build_ops_dashboard

        build_ops_dashboard(root_dir)
        return 0

    if args.command == "build-source-governance":
        from auto_report.app import cmd_build_source_governance

        cmd_build_source_governance(root_dir)
        return 0

    if args.command == "build-review-queue":
        from auto_report.app import cmd_build_review_queue

        cmd_build_review_queue(root_dir)
        return 0

    if args.command == "sync-feishu-workspace":
        from auto_report.app import cmd_sync_feishu_workspace

        cmd_sync_feishu_workspace(
            root_dir,
            publication_mode=getattr(args, "publication_mode", "") or "reviewed",
        )
        return 0

    if args.command == "sync-feishu-ops-desk":
        from auto_report.app import cmd_sync_feishu_ops_desk

        cmd_sync_feishu_ops_desk(root_dir)
        return 0

    if args.command == "pull-feishu-ops-status":
        from auto_report.app import cmd_pull_feishu_ops_status

        cmd_pull_feishu_ops_status(root_dir)
        return 0

    if args.command == "build-discovery-search":
        from auto_report.app import cmd_build_discovery_search

        cmd_build_discovery_search(root_dir, keywords_path=getattr(args, "keywords", ""))
        return 0

    if args.command == "evaluate-prompts":
        from auto_report.app import cmd_evaluate_prompts

        cmd_evaluate_prompts(root_dir, dataset_path=getattr(args, "dataset", ""))
        return 0

    if args.command == "apply-source-updates":
        from auto_report.app import cmd_apply_source_updates

        cmd_apply_source_updates(root_dir, dry_run=getattr(args, "dry_run", False))
        return 0

    if args.command == "run-watch-checks":
        from auto_report.app import cmd_run_watch_checks

        cmd_run_watch_checks(root_dir)
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
