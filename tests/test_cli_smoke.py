from auto_report.cli import build_parser


def test_cli_exposes_all_commands():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    # 原有命令
    assert "run-once" in choices
    assert "backfill" in choices
    assert "render-report" in choices
    assert "diagnose-delivery" in choices
    # CI 专用命令 (Phase 0)
    assert "collect-only" in choices
    assert "analyze-only" in choices
    assert "render-and-push" in choices
    assert "build-pages" in choices
    assert "build-ops-dashboard" in choices
    assert "build-source-governance" in choices
    assert "build-review-queue" in choices
    assert "build-discovery-search" in choices
    assert "evaluate-prompts" in choices


def test_ci_commands_exist():
    """验证 CI 子命令可被 argparse 正确解析（不执行实际逻辑）"""
    import sys
    from auto_report.cli import main

    for cmd in ["collect-only", "analyze-only", "render-and-push", "build-pages"]:
        old_argv = sys.argv
        try:
            sys.argv = ["auto-report", cmd]
            # 只验证能正确解析，不执行（main 内部依赖 CWD 下有 config/ 目录）
            parser = build_parser()
            args = parser.parse_args([cmd])
            assert args.command == cmd, f"Expected command '{cmd}', got '{args.command}'"
        finally:
            sys.argv = old_argv


def test_diagnose_delivery_command_accepts_mode_and_send_flag():
    parser = build_parser()

    args = parser.parse_args(["diagnose-delivery", "--mode", "full-report", "--send"])

    assert args.command == "diagnose-delivery"
    assert args.mode == "full-report"
    assert args.send is True


def test_diagnose_delivery_defaults_to_canary_mode():
    parser = build_parser()

    args = parser.parse_args(["diagnose-delivery"])

    assert args.command == "diagnose-delivery"
    assert args.mode == "canary"


def test_run_once_command_accepts_publication_mode():
    parser = build_parser()

    args = parser.parse_args(["run-once", "--publication-mode", "reviewed"])

    assert args.command == "run-once"
    assert args.publication_mode == "reviewed"


def test_run_once_command_accepts_review_metadata():
    parser = build_parser()

    args = parser.parse_args(
        [
            "run-once",
            "--publication-mode",
            "reviewed",
            "--reviewer",
            "Alice",
            "--review-note",
            "checked key sources",
        ]
    )

    assert args.command == "run-once"
    assert args.publication_mode == "reviewed"
    assert args.reviewer == "Alice"
    assert args.review_note == "checked key sources"


def test_backfill_command_accepts_publication_mode():
    parser = build_parser()

    args = parser.parse_args(["backfill", "--publication-mode", "reviewed"])

    assert args.command == "backfill"
    assert args.publication_mode == "reviewed"


def test_evaluate_prompts_command_accepts_dataset_path():
    parser = build_parser()

    args = parser.parse_args(["evaluate-prompts", "--dataset", "data/evals/sample.json"])

    assert args.command == "evaluate-prompts"
    assert args.dataset == "data/evals/sample.json"


def test_build_discovery_search_command_accepts_keywords_path():
    parser = build_parser()

    args = parser.parse_args(["build-discovery-search", "--keywords", "config/source_discovery/keywords.txt"])

    assert args.command == "build-discovery-search"
    assert args.keywords == "config/source_discovery/keywords.txt"
