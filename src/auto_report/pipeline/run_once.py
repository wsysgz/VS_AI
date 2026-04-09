from __future__ import annotations

from datetime import datetime, timezone


def build_run_status(generated_files: list[str], pushed: bool) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
    }
