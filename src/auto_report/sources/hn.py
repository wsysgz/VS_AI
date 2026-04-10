"""Hacker News 信息源采集器 — 抓取 Top / Show HN 热门条目"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.exceptions import RequestException

from auto_report.models.records import CollectedItem

# HN Firebase API endpoints
_HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
_HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

# 关键词过滤：只保留与 AI/芯片/开源/基础设施相关的条目
_RELEVANT_KEYWORDS = {
    # AI/ML
    "ai", "llm", "gpt", "claude", "gemini", "deepseek", "openai", "anthropic",
    "machine learning", "neural", "transformer", "diffusion", "inference",
    "training", "model", "token", "rag", "agent", "reasoning",
    "chip", "semiconductor", "gpu", "tpu", "nvidia", "amd", "intel", "qualcomm",
    "tsmc", "arm", "risc-v", "riscv", "silicon", "fabrication",
    "open source", "github", "infrastructur", "kubernetes", "docker",
    "database", "serverless", "cloud native", "devops", "observability",
    "rust", "python", "compiler", "runtime", "framework", "library",
    "security", "vulnerability", "encrypt", "privacy",
    "startup", "venture", "funding", "ipo", "acquisition",
    "apple", "google", "microsoft", "meta", "amazon", "aws",
}

# 噪音关键词：排除纯水帖/政治帖
_NOISE_KEYWORDS = {
    "ask hn", "show hn: who is hiring", "poll", "survey",
    "political", "election", "vote",
}


def _is_relevant(title: str) -> bool:
    """判断标题是否与目标领域相关"""
    title_lower = title.lower()
    # 先检查噪音
    for noise in _NOISE_KEYWORDS:
        if noise in title_lower:
            return False
    # 再检查相关性
    for kw in _RELEVANT_KEYWORDS:
        if kw in title_lower:
            return True
    return False


def _hn_item_to_collected(item: dict[str, Any]) -> CollectedItem | None:
    """将 HN item 转换为 CollectedItem"""
    title = item.get("title", "")
    url = item.get("url") or f"https://news.ycombinator.com/item?id={item['id']}"
    score = item.get("score", 0)
    comments = item.get("descendants", 0)
    item_id = str(item.get("id", ""))

    if not title or not item_id:
        return None

    # 时间转换（HN 用 Unix 秒）
    ts = item.get("time", 0)
    published_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)) if ts else ""

    # 构建摘要：包含分数和评论数
    summary_parts = [f"Score: {score}", f"Comments: {comments}"]
    if item.get("text"):
        text = item["text"][:300]
        summary_parts.append(f"Text: {text}")
    summary = " | ".join(summary_parts)

    # 标签
    tags = ["hacker-news"]
    if score >= 200:
        tags.append("trending")
    if score >= 500:
        tags.append("hot")
    if "Show HN" in title:
        tags.append("show-hn")

    return CollectedItem(
        source_id="hacker-news",
        item_id=f"hn-{item_id}",
        title=title,
        url=url,
        summary=summary,
        published_at=published_at,
        collected_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        tags=tags,
        language="en",
        metadata={
            "score": score,
            "comments": comments,
            "author": item.get("by", ""),
            "type": item.get("type", "story"),
        },
    )


def _filter_and_convert_items(
    raw_items: list[dict[str, Any]],
    max_items: int,
    min_score: int,
) -> tuple[list[CollectedItem], list[str]]:
    """
    过滤、转换、排序原始 HN 条目（纯逻辑，无网络调用，可独立测试）
    """
    relevant: list[CollectedItem] = []
    for raw in raw_items:
        title = raw.get("title", "")
        score = raw.get("score", 0)

        if score < min_score:
            continue
        if not _is_relevant(title):
            continue

        collected = _hn_item_to_collected(raw)
        if collected:
            relevant.append(collected)

    # 按 score 降序排列
    relevant.sort(key=lambda x: x.metadata.get("score", 0), reverse=True)
    return relevant[:max_items], []


def fetch_hn_top_stories(
    max_items: int = 30,
    min_score: int = 10,
) -> tuple[list[CollectedItem], list[str]]:
    """
    抓取 Hacker News Top Stories，返回相关条目。

    Args:
        max_items: 最大返回数量
        min_score: 最低分数阈值（低于此分数的条目跳过）

    Returns:
        (items, diagnostics)
    """
    items: list[CollectedItem] = []
    diagnostics: list[str] = []

    try:
        # 1. 获取 Top Stories ID 列表
        resp = requests.get(_HN_TOP_STORIES, timeout=15)
        resp.raise_for_status()
        story_ids = resp.json()

        if not story_ids:
            diagnostics.append("HN: empty top stories list")
            return items, diagnostics

        # 2. 并发抓取前 N 个故事的详情
        fetch_count = min(max_items * 3, len(story_ids))  # 多抓一些用于过滤
        candidate_ids = story_ids[:fetch_count]

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _fetch_item(sid: int) -> dict[str, Any] | None:
            try:
                r = requests.get(_HN_ITEM_URL.format(item_id=sid), timeout=10)
                r.raise_for_status()
                return r.json()
            except Exception:
                return None

        raw_items: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(_fetch_item, sid): sid for sid in candidate_ids}
            for future in as_completed(futures, timeout=30):
                result = future.result(timeout=5)
                if result and result.get("type") == "story":
                    raw_items.append(result)

        # 3. 过滤 + 排序 + 截断（使用纯逻辑函数）
        items, _filter_msgs = _filter_and_convert_items(raw_items, max_items, min_score)

        diagnostics.append(
            f"HN: fetched {len(raw_items)} raw, "
            f"filtered to {len(items)} relevant (min_score={min_score})"
        )

    except RequestException as exc:
        diagnostics.append(f"HN API request failed: {exc}")
    except Exception as exc:
        diagnostics.append(f"HN collection error: {exc}")

    return items, diagnostics
