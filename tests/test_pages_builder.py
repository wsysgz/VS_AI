from pathlib import Path

from auto_report.outputs.pages_builder import build_pages_site


def test_build_pages_site_preserves_existing_docs_content(tmp_path: Path):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "latest-summary.html").write_text(
        "<html><body><span>生成时间：2026-04-11T08:00:00+08:00<</span></body></html>",
        encoding="utf-8",
    )

    archives_dir = tmp_path / "data" / "archives" / "2026-04-10"
    archives_dir.mkdir(parents=True)
    (archives_dir / "2026-04-10T08-00-00-summary.html").write_text(
        "<html>old</html>",
        encoding="utf-8",
    )

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / ".nojekyll").write_text("", encoding="utf-8")
    (docs_dir / "HANDOFF.md").write_text("# handoff", encoding="utf-8")
    (docs_dir / "TECHNICAL_GUIDE.md").write_text("# guide", encoding="utf-8")
    superpowers_dir = docs_dir / "superpowers" / "status"
    superpowers_dir.mkdir(parents=True)
    (superpowers_dir / "session.md").write_text("keep me", encoding="utf-8")

    build_pages_site(tmp_path)

    assert (docs_dir / "HANDOFF.md").exists()
    assert (docs_dir / "TECHNICAL_GUIDE.md").exists()
    assert (superpowers_dir / "session.md").exists()
    assert (docs_dir / "index.html").exists()
    assert (
        docs_dir / "archives" / "2026-04-10" / "2026-04-10T08-00-00-summary.html"
    ).exists()


def test_build_pages_site_reports_recursive_archive_count(tmp_path: Path, capsys):
    reports_dir = tmp_path / "data" / "reports"
    reports_dir.mkdir(parents=True)
    (reports_dir / "latest-summary.html").write_text(
        "<html><body><span>生成时间：2026-04-11T08:00:00+08:00<</span></body></html>",
        encoding="utf-8",
    )

    archives_dir = tmp_path / "data" / "archives" / "2026-04-10"
    archives_dir.mkdir(parents=True)
    (archives_dir / "2026-04-10T08-00-00-summary.html").write_text(
        "<html>old</html>",
        encoding="utf-8",
    )

    build_pages_site(tmp_path)

    output = capsys.readouterr().out
    assert "[Pages] Archives: 2 files" in output
