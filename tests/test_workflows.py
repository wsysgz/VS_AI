from pathlib import Path

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]


def _load_workflow(name: str) -> dict[str, object]:
    return yaml.safe_load((ROOT_DIR / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def _workflow_on(workflow: dict[str, object]) -> dict[str, object]:
    return workflow.get("on", workflow.get(True, {}))


def test_collect_report_workflow_uses_offset_schedule():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert '- cron: "13 23 * * *"' in content


def test_collect_report_workflow_calls_reusable_foundation_jobs():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "uses: ./.github/workflows/reusable-workflow-guard.yml" in content
    assert "uses: ./.github/workflows/reusable-python-test.yml" in content
    assert "uses: ./.github/workflows/reusable-collect.yml" in content
    assert "uses: ./.github/workflows/reusable-analyze.yml" in content
    assert "uses: ./.github/workflows/reusable-report.yml" in content
    assert "uses: ./.github/workflows/reusable-pages.yml" in content
    assert "uses: ./.github/workflows/reusable-ops-dashboard.yml" in content
    assert "uses: ./.github/workflows/reusable-review-queue.yml" in content


def test_collect_report_workflow_keeps_schedule_and_dispatch_push_toggle():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-report.yml").read_text(encoding="utf-8")

    assert "AUTO_PUSH_ENABLED: ${{ inputs.auto_push_enabled }}" in content
    assert "PUBLICATION_MODE: ${{ inputs.publication_mode }}" in content
    assert "REPORT_REVIEWER: ${{ inputs.reviewer }}" in content
    assert "REPORT_REVIEW_NOTE: ${{ inputs.review_note }}" in content
    assert "SCHEDULER_TRIGGER_KIND: ${{ inputs.scheduler_trigger_kind }}" in content
    assert "SCHEDULER_COMPENSATION_RUN: ${{ inputs.scheduler_compensation_run }}" in content
    assert 'EXTERNAL_ENRICHMENT_ENABLED: "true"' in content
    assert 'EXTERNAL_ENRICHMENT_MAX_SIGNALS: "2"' in content
    assert 'EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS: "8"' in content


def test_reusable_report_workflow_accepts_boolean_scheduler_flags():
    workflow = _load_workflow("reusable-report.yml")
    inputs = _workflow_on(workflow)["workflow_call"]["inputs"]

    assert inputs["auto_push_enabled"]["type"] == "boolean"
    assert inputs["publication_mode"]["type"] == "string"
    assert inputs["reviewer"]["type"] == "string"
    assert inputs["review_note"]["type"] == "string"
    assert inputs["scheduler_compensation_run"]["type"] == "boolean"


def test_reusable_backfill_workflow_accepts_boolean_compensation_flag():
    workflow = _load_workflow("reusable-backfill.yml")
    inputs = _workflow_on(workflow)["workflow_call"]["inputs"]

    assert inputs["publication_mode"]["type"] == "string"
    assert inputs["reviewer"]["type"] == "string"
    assert inputs["review_note"]["type"] == "string"
    assert inputs["skip_push"]["type"] == "boolean"
    assert inputs["scheduler_compensation_run"]["type"] == "boolean"


def test_collect_and_backfill_workflows_pass_boolean_compensation_values():
    collect_workflow = _load_workflow("collect-report.yml")
    backfill_workflow = _load_workflow("backfill-report.yml")

    collect_with = collect_workflow["jobs"]["report"]["with"]
    backfill_with = backfill_workflow["jobs"]["backfill"]["with"]

    assert collect_with["publication_mode"] == "${{ github.event_name == 'workflow_dispatch' && inputs.publication_mode || 'auto' }}"
    assert collect_with["reviewer"] == "${{ github.event_name == 'workflow_dispatch' && inputs.reviewer || '' }}"
    assert collect_with["review_note"] == "${{ github.event_name == 'workflow_dispatch' && inputs.review_note || '' }}"
    assert backfill_with["publication_mode"] == "${{ inputs.publication_mode }}"
    assert backfill_with["reviewer"] == "${{ inputs.reviewer }}"
    assert backfill_with["review_note"] == "${{ inputs.review_note }}"
    assert collect_with["scheduler_compensation_run"] is False
    assert backfill_with["scheduler_compensation_run"] is False


def test_reusable_workflow_guard_runs_local_validation_script():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-workflow-guard.yml").read_text(encoding="utf-8")

    assert "scripts/check-workflows.ps1" in content


def test_reusable_python_test_workflow_uses_matrix_and_max_parallel():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-python-test.yml").read_text(encoding="utf-8")

    assert "strategy:" in content
    assert "max-parallel:" in content
    assert "matrix:" in content
    assert "python-version:" in content


def test_collect_report_workflow_creates_issue_for_all_channel_delivery_failure():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert 'FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: "true"' in content
    assert "actions/github-script@v9.0.0" in content
    assert "all delivery channels failed" in content


def test_collect_report_workflow_creates_issue_for_high_risk_report_with_run_status_summary():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "high risk report detected" in content
    assert "risk_level" in content
    assert "Stage status:" in content
    assert "Compensation run:" in content
    assert "Successful channels:" in content
    assert "Failed channels:" in content


def test_collect_report_reliability_issue_downloads_run_status_into_data_directory():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert 'name: final-report' in content
    assert 'path: data/' in content
    assert 'fs.readFileSync("data/state/run-status.json", "utf8")' in content


def test_collect_report_workflow_creates_review_issues_from_review_queue_artifact():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "review-queue" in content
    assert "review-issues.json" in content
    assert "[V7 review]" in content
    assert "high-value" in content
    assert "Issue already exists" in content


def test_backfill_workflow_calls_reusable_backfill_pipeline():
    content = (ROOT_DIR / ".github" / "workflows" / "backfill-report.yml").read_text(encoding="utf-8")

    assert "uses: ./.github/workflows/reusable-backfill.yml" in content


def test_reusable_backfill_workflow_builds_pages_and_ops_dashboard():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-backfill.yml").read_text(encoding="utf-8")

    assert 'run: python -m auto_report.cli backfill --target-date "${{ inputs.target_date }}"' in content
    assert "PUSHPLUS_SECRETKEY: ${{ secrets.PUSHPLUS_SECRETKEY }}" in content
    assert "TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}" in content
    assert "FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}" in content
    assert "REPORT_REVIEWER: ${{ inputs.reviewer }}" in content
    assert "REPORT_REVIEW_NOTE: ${{ inputs.review_note }}" in content
    assert "run: python -m auto_report.cli build-pages" in content
    assert "run: python -m auto_report.cli build-ops-dashboard" in content
    assert 'EXTERNAL_ENRICHMENT_ENABLED: "true"' in content
    assert 'EXTERNAL_ENRICHMENT_MAX_SIGNALS: "2"' in content
    assert 'EXTERNAL_ENRICHMENT_TIMEOUT_SECONDS: "8"' in content


def test_reusable_review_queue_workflow_builds_review_queue_artifact():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-review-queue.yml").read_text(encoding="utf-8")

    assert "name: final-report" in content
    assert "python -m auto_report.cli build-review-queue" in content
    assert "name: review-queue" in content


def test_reusable_ops_dashboard_workflow_uploads_source_governance_artifact():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-ops-dashboard.yml").read_text(encoding="utf-8")

    assert "python -m auto_report.cli build-source-governance" in content
    assert "name: source-governance" in content
    assert "path: out/source-governance/" in content


def test_reusable_report_workflow_replays_rendered_data_on_latest_branch_before_pushing():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-report.yml").read_text(encoding="utf-8")

    assert "PUSHPLUS_SECRETKEY: ${{ secrets.PUSHPLUS_SECRETKEY }}" in content
    assert "stefanzweifel/git-auto-commit-action@v4" not in content
    assert "mktemp -d" in content
    assert "for attempt in 1 2 3; do" in content
    assert 'git fetch origin "$GITHUB_REF_NAME"' in content
    assert 'git reset --hard "origin/$GITHUB_REF_NAME"' in content
    assert 'git clean -fd data/' in content
    assert 'cp -R "$rendered_data_dir"/. data/' in content
    assert 'git add data/' in content or 'git add data' in content
    assert 'git push origin HEAD:"$GITHUB_REF_NAME"' in content or 'git push origin HEAD:$GITHUB_REF_NAME' in content


def test_reusable_workflows_expose_helper_stage_ai_env_contract():
    analyze_content = (ROOT_DIR / ".github" / "workflows" / "reusable-analyze.yml").read_text(encoding="utf-8")
    report_content = (ROOT_DIR / ".github" / "workflows" / "reusable-report.yml").read_text(encoding="utf-8")

    for content in (analyze_content, report_content):
        assert "PREFILTER_AI_PROVIDER: ${{ vars.PREFILTER_AI_PROVIDER || '' }}" in content
        assert "PREFILTER_AI_BASE_URL: ${{ vars.PREFILTER_AI_BASE_URL || '' }}" in content
        assert "PREFILTER_AI_MODEL: ${{ vars.PREFILTER_AI_MODEL || '' }}" in content
        assert "PREFILTER_AI_API_KEY: ${{ secrets.PREFILTER_AI_API_KEY }}" in content
        assert "DISCOVERY_AI_PROVIDER: ${{ vars.DISCOVERY_AI_PROVIDER || '' }}" in content
        assert "DISCOVERY_AI_BASE_URL: ${{ vars.DISCOVERY_AI_BASE_URL || '' }}" in content
        assert "DISCOVERY_AI_MODEL: ${{ vars.DISCOVERY_AI_MODEL || '' }}" in content
        assert "DISCOVERY_AI_API_KEY: ${{ secrets.DISCOVERY_AI_API_KEY }}" in content
        assert "SEARCH_AI_PROVIDER: ${{ vars.SEARCH_AI_PROVIDER || '' }}" in content
        assert "SEARCH_AI_BASE_URL: ${{ vars.SEARCH_AI_BASE_URL || '' }}" in content
        assert "SEARCH_AI_MODEL: ${{ vars.SEARCH_AI_MODEL || '' }}" in content
        assert "SEARCH_AI_API_KEY: ${{ secrets.SEARCH_AI_API_KEY }}" in content


def test_reusable_pages_workflow_syncs_current_branch_and_commits_all_pages_outputs():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-pages.yml").read_text(encoding="utf-8")

    assert 'git pull --rebase origin "$GITHUB_REF_NAME"' in content
    assert "docs/weekly/" in content
    assert "docs/special/" in content
    assert "docs/search-index.json" in content
    assert "docs/feed.json" in content
    assert "docs/rss.xml" in content
    assert "if git diff --cached --quiet; then" in content


def test_collect_report_followup_issue_jobs_only_run_when_artifacts_exist():
    content = (ROOT_DIR / ".github" / "workflows" / "collect-report.yml").read_text(encoding="utf-8")

    assert "if: always() && needs.report.result == 'success'" in content
    assert "if: always() && needs.review-queue.result == 'success'" in content


def test_reusable_backfill_workflow_replays_rendered_outputs_on_latest_branch_before_pushing():
    content = (ROOT_DIR / ".github" / "workflows" / "reusable-backfill.yml").read_text(encoding="utf-8")

    assert "stefanzweifel/git-auto-commit-action@v4" not in content
    assert "mktemp -d" in content
    assert "for attempt in 1 2 3; do" in content
    assert 'git fetch origin "$GITHUB_REF_NAME"' in content
    assert 'git reset --hard "origin/$GITHUB_REF_NAME"' in content
    assert 'git clean -fd data/ docs/index.html docs/archives/ docs/weekly/ docs/special/ docs/search-index.json docs/feed.json docs/rss.xml docs/.nojekyll' in content
    assert 'cp -R "$rendered_artifacts_dir/data"/. data/' in content
    assert 'cp -R "$rendered_artifacts_dir/docs/archives"/. docs/archives/' in content
    assert 'git add data/ docs/index.html docs/archives/ docs/weekly/ docs/special/ docs/search-index.json docs/feed.json docs/rss.xml docs/.nojekyll' in content
    assert 'git commit -m "chore: backfill report for ${{ inputs.target_date || \'latest\' }} [skip ci]"' in content
    assert 'git push origin HEAD:"$GITHUB_REF_NAME"' in content or 'git push origin HEAD:$GITHUB_REF_NAME' in content


def test_compensation_workflow_sets_scheduler_context_and_issue_rule():
    content = (ROOT_DIR / ".github" / "workflows" / "compensate-report.yml").read_text(encoding="utf-8")

    assert "SCHEDULER_TRIGGER_KIND: compensation" in content
    assert "SCHEDULER_COMPENSATION_RUN: \"true\"" in content
    assert "PUSHPLUS_SECRETKEY: ${{ secrets.PUSHPLUS_SECRETKEY }}" in content
    assert "actions/github-script@v9.0.0" in content
    assert "consecutive compensation failures" in content
    assert "stefanzweifel/git-auto-commit-action@v4" not in content
    assert "mktemp -d" in content
    assert "for attempt in 1 2 3; do" in content
    assert 'git fetch origin "$GITHUB_REF_NAME"' in content
    assert 'git reset --hard "origin/$GITHUB_REF_NAME"' in content
    assert 'git clean -fd data/ docs/index.html docs/archives/ docs/weekly/ docs/special/ docs/search-index.json docs/feed.json docs/rss.xml docs/.nojekyll' in content
    assert 'cp -R "$rendered_artifacts_dir/data"/. data/' in content
    assert 'cp -R "$rendered_artifacts_dir/docs/special"/. docs/special/' in content
    assert 'git add data/ docs/index.html docs/archives/ docs/weekly/ docs/special/ docs/search-index.json docs/feed.json docs/rss.xml docs/.nojekyll' in content
    assert 'git commit -m "chore: compensate daily report [skip ci]"' in content
    assert 'git push origin HEAD:"$GITHUB_REF_NAME"' in content or 'git push origin HEAD:$GITHUB_REF_NAME' in content


def test_canary_workflow_uses_canary_mode_and_issue_rule():
    content = (ROOT_DIR / ".github" / "workflows" / "delivery-canary.yml").read_text(encoding="utf-8")

    assert "--mode canary --send" in content
    assert "PUSHPLUS_SECRETKEY: ${{ secrets.PUSHPLUS_SECRETKEY }}" in content
    assert "actions/github-script@v9.0.0" in content
    assert "consecutive canary failures" in content


def test_source_reachability_canary_probes_google_and_openvino_from_github_runner():
    content = (ROOT_DIR / ".github" / "workflows" / "source-reachability-canary.yml").read_text(encoding="utf-8")

    assert 'name: Source Reachability Canary' in content
    assert 'https://blog.google/innovation-and-ai/technology/ai/rss/' in content
    assert 'https://blog.openvino.ai/' in content
    assert 'https://blog.openvino.ai/feed' not in content
    assert 'https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw' not in content
    assert 'https://www.youtube.com/feeds/videos.xml?user=nvidia' not in content
    assert 'https://www.youtube.com/feeds/videos.xml?user=Microsoftdeveloper' not in content
    assert 'https://www.youtube.com/feeds/videos.xml?user=pytorch' not in content
    assert 'actions/upload-artifact@v4' in content
    assert 'source-reachability-report' in content
    assert 'urllib.request' in content
    assert 'import requests' not in content
