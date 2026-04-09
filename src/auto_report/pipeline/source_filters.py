from __future__ import annotations


NOISE_TITLES = {
    "home",
    "subscribe",
    "pricing",
    "docs",
    "jobs",
    "about",
    "skip to main content",
}


def should_keep_candidate(title: str, url: str, source: dict[str, object]) -> bool:
    normalized_title = title.strip().lower()
    normalized_url = url.strip().lower()

    if not normalized_title or normalized_title in NOISE_TITLES or len(normalized_title) < 8:
        return False
    if normalized_url.endswith("#") or "#content" in normalized_url:
        return False

    include_patterns = [str(item).lower() for item in source.get("include_url_patterns", [])]
    exclude_patterns = [str(item).lower() for item in source.get("exclude_url_patterns", [])]

    if include_patterns and not any(pattern in normalized_url for pattern in include_patterns):
        return False
    if any(pattern in normalized_url for pattern in exclude_patterns):
        return False
    return True
