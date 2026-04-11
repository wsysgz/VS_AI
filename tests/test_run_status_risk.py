from auto_report.pipeline.run_once import build_run_status


def test_build_run_status_includes_risk_level():
    status = build_run_status(
        generated_files=["data/reports/latest-summary.md"],
        pushed=False,
        risk_level="medium",
    )

    assert status["risk_level"] == "medium"
