"""Hacker News 采集器测试"""

from unittest.mock import patch, MagicMock

import pytest

from auto_report.sources.hn import (
    _filter_and_convert_items,
    _is_relevant,
    _hn_item_to_collected,
    fetch_hn_top_stories,
)


# ── 相关性过滤测试 ────────────────────────────────

class TestHnRelevanceFilter:
    def test_ai_keywords_match(self):
        assert _is_relevant("GPT-5 achieves new SOTA on reasoning") is True
        assert _is_relevant("Nvidia announces Blackwell GPU") is True

    def test_chip_keywords_match(self):
        assert _is_relevant("TSMC 2nm process yields improve") is True
        assert _is_relevant("RISC-V gains traction in embedded") is True

    def test_infra_keywords_match(self):
        assert _is_relevant("Kubernetes 1.30 released") is True
        assert _is_relevant("New Rust async runtime benchmarks") is True

    def test_noise_filtered_out(self):
        assert _is_relevant("Ask HN: Who is hiring? (April 2026)") is False
        assert _is_relevant("Poll: What's your favorite editor?") is False
        assert _is_relevant("Political discussion about elections") is False

    def test_irrelevant_topics_no_match(self):
        # 纯生活类话题，不含任何关键词
        assert _is_relevant("I bought a house and here's what happened") is False


# ── 数据转换测试 ─────────────────────────────────

class TestHnItemConversion:
    def _make_item(self, **overrides):
        base = {
            "id": 42,
            "title": "Test AI Story",
            "url": "https://example.com/ai",
            "score": 123,
            "descendants": 45,
            "by": "testuser",
            "time": 1744368000,  # fixed timestamp
            "type": "story",
            "text": None,
        }
        base.update(overrides)
        return base

    def test_basic_conversion(self):
        item = self._make_item()
        result = _hn_item_to_collected(item)
        assert result is not None
        assert result.source_id == "hacker-news"
        assert result.item_id == "hn-42"
        assert result.title == "Test AI Story"
        assert result.url == "https://example.com/ai"
        assert result.language == "en"

    def test_fallback_url_when_missing(self):
        """没有 url 时用 HN 评论页"""
        item = self._make_item(url=None)
        result = _hn_item_to_collected(item)
        assert result is not None
        assert "news.ycombinator.com" in result.url

    def test_tags_include_score_based_badges(self):
        normal = self._make_item(score=100)
        trending = self._make_item(score=250)
        hot = self._make_item(score=600)

        r1 = _hn_item_to_collected(normal)
        r2 = _hn_item_to_collected(trending)
        r3 = _hn_item_to_collected(hot)

        assert "trending" not in r1.tags
        assert "trending" in r2.tags
        assert "hot" in r3.tags

    def test_show_hn_tag(self):
        item = self._make_item(title="Show HN: My new AI tool")
        result = _hn_item_to_collected(item)
        assert "show-hn" in result.tags

    def test_none_for_empty_title(self):
        item = self._make_item(title="")
        assert _hn_item_to_collected(item) is None


# ── 集成测试（Mock API） ─────────────────────────

class TestFetchHnTopStories:
    def test_filter_and_sort(self):
        """测试过滤+排序的纯逻辑（无需 mock 网络调用）"""
        raw_items = [
            {"id": 1, "title": "Amazing GPT-5 breakthrough", "url": "http://ex.com/a",
             "score": 500, "descendants": 200, "by": "user1", "time": 1744368000,
             "type": "story", "text": None},
            {"id": 2, "title": "TSMC 2nm yields hit 80%", "url": "http://ex.com/b",
             "score": 300, "descendants": 150, "by": "user2", "time": 1744368000,
             "type": "story", "text": None},
            {"id": 3, "title": "Ask HN: Who wants pizza?", "url": "http://ex.com/c",
             "score": 5, "descendants": 3, "by": "user3", "time": 1744368000,
             "type": "story", "text": None},  # 噪音 + 低分
            {"id": 4, "title": "I bought a boat yesterday", "url": "http://ex.com/d",
             "score": 50, "descendants": 20, "by": "user4", "time": 1744368000,
             "type": "story", "text": None},  # 不相关
            {"id": 5, "title": "Show HN: My Rust AI framework", "url": "http://ex.com/e",
             "score": 120, "descendants": 60, "by": "user5", "time": 1744368000,
             "type": "story", "text": None},
        ]

        items, msgs = _filter_and_convert_items(raw_items, max_items=10, min_score=10)

        # 应该拿到 3 个相关条目 (id 1, 2, 5)
        assert len(items) == 3
        titles = {i.title for i in items}
        assert "Amazing GPT-5 breakthrough" in titles
        assert "TSMC 2nm yields hit 80%" in titles
        assert "Show HN: My Rust AI framework" in titles

        # 按分数降序排列 (500 > 300 > 120)
        assert items[0].metadata["score"] == 500
        assert items[1].metadata["score"] == 300
        assert items[2].metadata["score"] == 120

    def test_max_items_truncation(self):
        """测试 max_items 截断"""
        raw_items = [
            {"id": i, "title": f"AI news #{i}", "url": f"http://ex.com/{i}",
             "score": 100 + i * 10, "descendants": i, "by": "u", "time": 1744368000,
             "type": "story", "text": None}
            for i in range(1, 6)  # 5 条
        ]
        items, _ = _filter_and_convert_items(raw_items, max_items=2, min_score=1)
        assert len(items) == 2

    @patch("auto_report.sources.hn.requests.get")
    def test_api_failure_returns_empty(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        items, diagnostics = fetch_hn_top_stories()
        assert len(items) == 0
        assert any("error" in d.lower() for d in diagnostics)

    @patch("auto_report.sources.hn.requests.get")
    def test_empty_list_graceful(self, mock_get):
        resp = MagicMock()
        resp.json.return_value = []
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp

        items, diagnostics = fetch_hn_top_stories()
        assert len(items) == 0
        assert any("empty" in d.lower() for d in diagnostics)
