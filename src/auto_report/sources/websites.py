from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from auto_report.models.records import CollectedItem


def extract_listing_items(
    source_id: str,
    html: str,
    page_url: str,
    category_hint: str,
) -> list[CollectedItem]:
    soup = BeautifulSoup(html, "html.parser")
    collected_at = datetime.now(timezone.utc).isoformat()
    items: list[CollectedItem] = []

    for index, anchor in enumerate(soup.find_all("a", href=True)):
        title = anchor.get_text(" ", strip=True)
        href = urljoin(page_url, anchor["href"])
        if not title or not href:
            continue
        items.append(
            CollectedItem(
                source_id=source_id,
                item_id=f"{source_id}:{index}",
                title=title,
                url=href,
                summary="",
                published_at=collected_at,
                collected_at=collected_at,
                tags=[category_hint] if category_hint else [],
                language="unknown",
                metadata={"page_url": page_url},
            )
        )
    return items
