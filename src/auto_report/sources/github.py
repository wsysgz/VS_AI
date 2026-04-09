from __future__ import annotations

from datetime import datetime, timezone

from auto_report.models.records import CollectedItem


def normalize_github_repositories(
    source_id: str,
    payload: dict[str, object],
    category_hint: str,
) -> list[CollectedItem]:
    items: list[CollectedItem] = []
    collected_at = datetime.now(timezone.utc).isoformat()

    for index, repo in enumerate(payload.get("items", [])):
        if not isinstance(repo, dict):
            continue
        tags = [str(tag) for tag in repo.get("topics", [])]
        if category_hint and category_hint not in tags:
            tags.append(category_hint)
        items.append(
            CollectedItem(
                source_id=source_id,
                item_id=f"{source_id}:{index}",
                title=str(repo.get("full_name", "")).strip(),
                url=str(repo.get("html_url", "")).strip(),
                summary=str(repo.get("description", "") or "").strip(),
                published_at=str(repo.get("updated_at", collected_at)),
                collected_at=collected_at,
                tags=tags,
                language=str(repo.get("language", "") or "unknown"),
                metadata={
                    "stars": int(repo.get("stargazers_count", 0) or 0),
                },
            )
        )
    return [item for item in items if item.title and item.url]
