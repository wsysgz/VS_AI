from auto_report.cli import build_parser


def test_cli_exposes_all_commands():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    # 原有命令
    assert "run-once" in choices
    assert "backfill" in choices
    assert "render-report" in choices
    # CI 专用命令 (Phase 0)
    assert "collect-only" in choices
    assert "analyze-only" in choices
    assert "render-and-push" in choices
    assert "build-pages" in choices


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
