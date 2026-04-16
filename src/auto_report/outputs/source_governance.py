from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from auto_report.settings import load_settings
from auto_report.source_registry import build_source_governance_queue, build_source_registry


def build_source_governance_artifact(root_dir: Path) -> Path:
    settings = load_settings(root_dir)
    source_registry = build_source_registry(settings)
    source_governance = build_source_governance_queue(source_registry)

    output_dir = root_dir / "out" / "source-governance"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "source-governance.json"
    output_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "source_registry": source_registry,
                "source_governance": source_governance,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_path
