from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_collect_report_workflow_uses_schedule_or_dispatch_push_toggle():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "AUTO_PUSH_ENABLED: ${{ github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.push_enabled == true) }}" in content


def test_collect_report_workflow_commits_docs_nojekyll_file():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "git add docs/index.html docs/archives/ docs/.nojekyll" in content


def test_collect_report_workflow_does_not_depend_on_missing_test_results_action():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "dorny/test-results-action" not in content
    assert "name: Upload test results artifact" in content
    assert "path: test-results.xml" in content


def test_collect_report_workflow_rebases_pages_commit_before_push():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "git pull --rebase origin main" in content


def test_collect_report_workflow_pulls_main_before_staging_pages_changes():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    pull_index = content.index("git pull --rebase origin main")
    add_index = content.index("git add docs/index.html docs/archives/ docs/.nojekyll")

    assert pull_index < add_index


def test_collect_report_workflow_pulls_main_before_downloading_final_data():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    pull_index = content.index("git pull --rebase origin main")
    download_index = content.index("- name: Download final data")

    assert pull_index < download_index


def test_backfill_workflow_runs_backfill_cli():
    content = (ROOT_DIR / ".github" / "workflows" / "backfill-report.yml").read_text(encoding="utf-8")

    assert 'run: python -m auto_report.cli backfill --target-date "${{ inputs.target_date }}"' in content
