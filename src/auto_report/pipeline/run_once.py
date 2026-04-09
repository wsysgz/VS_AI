from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_run_status(
    generated_files: list[str],
    pushed: bool,
    push_channel: str = "",
    push_response: dict[str, Any] | None = None,
) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_files": generated_files,
        "pushed": pushed,
        "push_channel": push_channel,
        "push_response": push_response or {},
    }
