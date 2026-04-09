from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from auto_report.models.records import CollectedItem
from auto_report.pipeline.source_filters import should_keep_candidate

CARD_PREFIX_PATTERN = re.compile(
    r"^(?:(?:Announcements?|Product|Policy|Research|Company|Press|News)\s+)?"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\s+"
    r"(?:(?:Announcements?|Product|Policy|Research|Company|Press|News)\s+)?",
    re.IGNORECASE,
)


def _extract_title(anchor: object) -> str:
    heading = anchor.select_one("h1, h2, h3, h4, h5, h6")
    if heading is not None:
        return heading.get_text(" ", strip=True)

    title = anchor.get_text(" ", strip=True)
    title = CARD_PREFIX_PATTERN.sub("", title).strip()
    return " ".join(title.split())


def extract_listing_items(source: dict[str, object], html: str) -> list[CollectedItem]:
    soup = BeautifulSoup(html, "html.parser")
    collected_at = datetime.now(timezone.utc).isoformat()
    source_id = str(source["id"])
    page_url = str(source["url"])
    category_hint = str(source.get("category_hint", ""))
    selector = str(source.get("link_selector", "a[href]"))
    items: list[CollectedItem] = []

    for index, anchor in enumerate(soup.select(selector)):
        title = _extract_title(anchor)
        href = anchor.get("href")
        if not href:
            continue
        href = urljoin(page_url, href)
        if not title or not href:
            continue
        if not should_keep_candidate(title, href, source):
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
