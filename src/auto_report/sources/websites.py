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


def _normalize_published_at(node: object, *, fallback: str) -> str:
    if node is None:
        return fallback

    datetime_value = getattr(node, "get", lambda *_args, **_kwargs: None)("datetime")
    if isinstance(datetime_value, str) and datetime_value.strip():
        return datetime_value.strip()

    text = node.get_text(" ", strip=True)
    return " ".join(text.split()) if text else fallback


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


def extract_structured_items(source: dict[str, object], html: str) -> list[CollectedItem]:
    soup = BeautifulSoup(html, "html.parser")
    collected_at = datetime.now(timezone.utc).isoformat()
    source_id = str(source["id"])
    page_url = str(source["url"])
    category_hint = str(source.get("category_hint", ""))
    entry_selector = str(source.get("entry_selector", "")).strip() or "article"
    title_selector = str(source.get("title_selector", "")).strip()
    link_selector = str(source.get("link_selector", "")).strip() or "a[href]"
    date_selector = str(source.get("date_selector", "")).strip()
    entry_link_is_self = bool(source.get("entry_link_is_self", False))
    items: list[CollectedItem] = []

    for index, entry in enumerate(soup.select(entry_selector)):
        title_node = entry.select_one(title_selector) if title_selector else entry
        link_node = entry if entry_link_is_self else entry.select_one(link_selector)
        date_node = entry.select_one(date_selector) if date_selector else None

        title = _extract_title(title_node) if title_node is not None else ""
        href = link_node.get("href") if link_node is not None else None
        if not href:
            continue
        href = urljoin(page_url, href)
        if not title or not href:
            continue
        if not should_keep_candidate(title, href, source):
            continue

        published_at = _normalize_published_at(date_node, fallback=collected_at)
        items.append(
            CollectedItem(
                source_id=source_id,
                item_id=f"{source_id}:{index}",
                title=title,
                url=href,
                summary="",
                published_at=published_at,
                collected_at=collected_at,
                tags=[category_hint] if category_hint else [],
                language="unknown",
                metadata={"page_url": page_url},
            )
        )
    return items


def _lookup_json_path(payload: object, path: list[str]) -> object:
    current = payload
    for part in path:
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list):
            try:
                index = int(part)
            except (TypeError, ValueError):
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def _lookup_field(item: dict[str, object], field: str) -> object:
    current: object = item
    for part in field.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def extract_json_items(source: dict[str, object], payload: dict[str, object]) -> list[CollectedItem]:
    collected_at = datetime.now(timezone.utc).isoformat()
    source_id = str(source["id"])
    category_hint = str(source.get("category_hint", ""))
    page_url = str(source.get("url", ""))
    items_path = [str(part) for part in source.get("json_items_path", [])]
    items_slice_start = int(source.get("json_items_slice_start", 0))
    title_field = str(source.get("item_title_field", "title"))
    link_field = str(source.get("item_link_field", "path"))
    link_template = str(source.get("item_link_template", "{value}"))
    date_field = str(source.get("item_date_field", "")).strip()

    raw_items = _lookup_json_path(payload, items_path)
    if isinstance(raw_items, list):
        iterable_items = raw_items[items_slice_start:]
    else:
        iterable_items = raw_items
    if not isinstance(iterable_items, list):
        return []

    items: list[CollectedItem] = []
    for index, raw_item in enumerate(iterable_items):
        if not isinstance(raw_item, dict):
            continue
        title_value = _lookup_field(raw_item, title_field)
        link_value = _lookup_field(raw_item, link_field)
        if not isinstance(title_value, str) or not isinstance(link_value, str):
            continue
        title = " ".join(title_value.split())
        href = link_template.format(value=link_value.strip())
        if not should_keep_candidate(title, href, source):
            continue
        published_at = collected_at
        if date_field:
            date_value = _lookup_field(raw_item, date_field)
            if isinstance(date_value, str) and date_value.strip():
                published_at = date_value.strip()
        items.append(
            CollectedItem(
                source_id=source_id,
                item_id=f"{source_id}:{index}",
                title=title,
                url=href,
                summary="",
                published_at=published_at,
                collected_at=collected_at,
                tags=[category_hint] if category_hint else [],
                language="unknown",
                metadata={"page_url": page_url, "source_mode": "json_api"},
            )
        )
    return items
