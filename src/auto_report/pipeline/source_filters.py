from __future__ import annotations

import re


NOISE_TITLES = {
    "home",
    "subscribe",
    "pricing",
    "docs",
    "jobs",
    "about",
    "skip to main content",
}

NOISE_TITLE_PATTERNS = {
    "webinar",
    "register",
    "event",
    "ebook",
    "white paper",
    "press release",
    "partner",
    "sponsor",
}


def _matches_noise_title_pattern(title: str) -> bool:
    for pattern in NOISE_TITLE_PATTERNS:
        escaped = re.escape(pattern).replace(r"\ ", r"\s+")
        if re.search(rf"\b{escaped}\b", title):
            return True
    return False


def should_keep_candidate(title: str, url: str, source: dict[str, object]) -> bool:
    normalized_title = title.strip().lower()
    normalized_url = url.strip().lower()

    if not normalized_title or normalized_title in NOISE_TITLES or len(normalized_title) < 8:
        return False
    if _matches_noise_title_pattern(normalized_title):
        return False
    if normalized_url.endswith("#") or "#content" in normalized_url:
        return False

    include_patterns = [str(item).lower() for item in source.get("include_url_patterns", [])]
    exclude_patterns = [str(item).lower() for item in source.get("exclude_url_patterns", [])]
    include_title_patterns = [str(item).lower() for item in source.get("include_title_patterns", [])]
    exclude_title_patterns = [str(item).lower() for item in source.get("exclude_title_patterns", [])]

    if include_patterns and not any(pattern in normalized_url for pattern in include_patterns):
        return False
    if any(pattern in normalized_url for pattern in exclude_patterns):
        return False
    if include_title_patterns and not any(pattern in normalized_title for pattern in include_title_patterns):
        return False
    if any(pattern in normalized_title for pattern in exclude_title_patterns):
        return False
    return True
