from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_collect_report_workflow_uses_schedule_or_dispatch_push_toggle():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "AUTO_PUSH_ENABLED: ${{ github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.push_enabled == true) }}" in content


def test_collect_report_workflow_commits_docs_nojekyll_file():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "git add docs/index.html docs/archives/ docs/.nojekyll" in content


def test_backfill_workflow_runs_backfill_cli():
    content = (ROOT_DIR / ".github" / "workflows" / "backfill-report.yml").read_text(encoding="utf-8")

    assert 'run: python -m auto_report.cli backfill --target-date "${{ inputs.target_date }}"' in content
