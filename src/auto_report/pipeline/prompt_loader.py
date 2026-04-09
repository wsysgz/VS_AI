from __future__ import annotations

from pathlib import Path


STAGE_FILE_NAMES = {
    "analysis": "analysis-before.md",
    "summary": "summary-before.md",
    "forecast": "forecast-before.md",
}


def load_ai_readings(root_dir: Path) -> dict[str, str]:
    base_dir = root_dir / "config" / "ai_reading"
    readings: dict[str, str] = {}
    for stage, file_name in STAGE_FILE_NAMES.items():
        path = base_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing AI reading asset for {stage}: {path}")
        readings[stage] = path.read_text(encoding="utf-8").strip()
    return readings
