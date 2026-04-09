from auto_report.cli import build_parser


def test_cli_exposes_run_and_backfill_commands():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert "run-once" in choices
    assert "backfill" in choices
    assert "render-report" in choices
