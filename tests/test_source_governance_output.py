import json
import shutil
from pathlib import Path

from auto_report.outputs.source_governance import build_source_governance_artifact


def test_build_source_governance_artifact_writes_json(tmp_path: Path):
    root = Path.cwd()
    shutil.copytree(root / "config", tmp_path / "config")

    output_path = build_source_governance_artifact(tmp_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path == tmp_path / "out" / "source-governance" / "source-governance.json"
    assert "generated_at" in payload
    assert "source_registry" in payload
    assert "source_governance" in payload
    assert "changedetection_candidates" in payload["source_governance"]
