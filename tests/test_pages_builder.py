import json
from pathlib import Path

from auto_report.outputs.pages_builder import build_pages_site


def _sample_payload(
    date_text: str,
    domain: str,
    host_title: str,
    publication_mode: str = "auto",
    one_line_core: str | None = None,
    reviewer: str = "",
    review_note: str = "",
) -> dict[str, object]:
    return {
        "meta": {
            "generated_at": f"{date_text}T08:00:00+08:00",
            "timezone": "Asia/Shanghai",
            "total_items": 12,
            "total_topics": 4,
            "publication_mode": publication_mode,
            "review": {
                "reviewer": reviewer,
                "review_note": review_note,
            },
        },
        "one_line_core": one_line_core or f"{host_title} 成为本轮最强主线。",
        "executive_summary": [
            f"{host_title} 正在推动新的工程周期。",
            "公开站需要支持长期检索与归档阅读。",
        ],
        "key_points": [
            {"title": "主线继续抬升", "why_it_matters": "说明市场关注度保持集中"},
            {"title": "基础设施开始成熟", "why_it_matters": "工程落地条件改善"},
        ],
        "key_insights": [
            "信息架构已经从日报转向可持续阅读站。",
        ],
        "analyses": [
            {
                "title": f"{host_title} 平台更新",
                "primary_domain": domain,
                "primary_contradiction": "速度 vs 稳定性",
                "core_insight": f"{host_title} 在提升发布节奏的同时开始补工程闭环。",
                "confidence": "medium",
                "url": f"https://example.com/{host_title.lower().replace(' ', '-')}",
            }
        ],
        "forecast": {
            "most_likely_case": "未来一周仍将围绕交付可靠性和内容密度迭代。",
            "forecast_conclusion": "继续观察高价值主题的延续性。",
            "key_variables": ["搜索体验", "归档覆盖", "信号密度"],
        },
        "limitations": [
            "部分主题仍需复核",
        ],
        "actions": [
            "继续跟踪高价值主题",
        ],
        "signals": [
            {
                "title": f"{host_title} 发布新版本",
                "url": f"https://news.example.com/{host_title.lower().replace(' ', '-')}/launch",
                "summary": f"{host_title} 发布新版本，强调推理效率与稳定交付。",
                "primary_domain": domain,
                "matched_domains": [domain],
                "score": 3.2,
                "evidence_count": 3,
                "lifecycle_state": "verified",
                "risk_level": "low",
                "enrichment_summary": "2 source(s) | official / repo",
                "tags": [domain, "release", "infra"],
            },
            {
                "title": f"{host_title} 推出归档检索",
                "url": f"https://blog.example.com/{host_title.lower().replace(' ', '-')}/archives",
                "summary": f"{host_title} 开始强化归档与搜索能力。",
                "primary_domain": domain,
                "matched_domains": [domain],
                "score": 2.1,
                "evidence_count": 2,
                "lifecycle_state": "rising",
                "risk_level": "high",
                "enrichment_summary": "1 source(s) | community",
                "tags": [domain, "search", "archives"],
            },
        ],
        "predictions": [
            "搜索与归档会成为日报站点的关键分水岭。",
        ],
        "stage_status": {
            "analysis": "ok",
            "summary": "ok",
            "forecast": "ok",
        },
    }


def _with_comparison_brief(payload: dict[str, object]) -> dict[str, object]:
    payload["comparison_brief"] = {
        "cn_highlights": [
            "国内侧：DeepSeek 与 ModelScope 继续强化中文模型生态。"
        ],
        "intl_highlights": [
            "海外侧：OpenAI 与 Microsoft Research 继续推进智能体可靠性工程。"
        ],
        "head_to_head": [
            {
                "track": "智能体可靠性",
                "cn": "国内更关注模型生态和应用落地。",
                "intl": "海外更关注沙箱、调试和运行时安全。",
                "delta": "国内需要补齐可观测性与安全工具链信号。",
            }
        ],
        "gaps": [
            "智能体可靠性：国内侧工程调试信号偏少。"
        ],
        "watchpoints": [
            "观察国内厂商是否补充沙箱执行、调试框架和安全网关。"
        ],
    }
    return payload


def _with_english_comparison_brief(payload: dict[str, object]) -> dict[str, object]:
    payload["comparison_brief"] = {
        "cn_highlights": [
            {
                "title": "Espressif Documentation MCP Server: Power Your AI Agents with Espressif Docs",
                "tech_track": "embedded",
                "source_ids": ["espressif-blog"],
            }
        ],
        "intl_highlights": [
            {
                "title": "Automations",
                "tech_track": "frontier-ai",
                "source_ids": ["openai-news"],
            }
        ],
        "head_to_head": [
            {
                "tech_track": "frontier-ai",
                "cn_title": "Agent 新进展：跨 app、跨设备、更多玩法｜智谱 Agent OpenDay",
                "intl_title": "Automations",
                "cn_source_ids": ["zhipu-news"],
                "intl_source_ids": ["openai-news"],
            }
        ],
        "gaps": ["compute-infra：仅看到海外信号，需补齐国内来源。"],
        "watchpoints": ["继续跟踪 frontier-ai 的国内外同轨发布、生态采用与真实交付反馈。"],
    }
    return payload


def _write_report_set(root: Path, archive_date: str, payload: dict[str, object]) -> None:
    reports_dir = root / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    archives_dir = root / "data" / "archives" / archive_date
    archives_dir.mkdir(parents=True, exist_ok=True)

    html_stub = f"<html><body><span>生成时间：{payload['meta']['generated_at']}<</span></body></html>"
    report_name = f"{payload['meta']['generated_at'].replace(':', '-')}-summary"

    (reports_dir / "latest-summary.html").write_text(html_stub, encoding="utf-8")
    (reports_dir / "latest-summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (archives_dir / f"{report_name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (archives_dir / f"{report_name}.html").write_text(html_stub, encoding="utf-8")


def _write_track_report_set(root: Path, archive_date: str, payload: dict[str, object], publication_mode: str) -> None:
    reports_dir = root / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    archives_dir = root / "data" / "archives" / archive_date
    archives_dir.mkdir(parents=True, exist_ok=True)

    html_stub = f"<html><body><span>生成时间：{payload['meta']['generated_at']}<</span></body></html>"
    report_name = f"{payload['meta']['generated_at'].replace(':', '-')}-summary-{publication_mode}"

    (reports_dir / f"latest-summary-{publication_mode}.html").write_text(html_stub, encoding="utf-8")
    (reports_dir / f"latest-summary-{publication_mode}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (archives_dir / f"{report_name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (archives_dir / f"{report_name}.html").write_text(html_stub, encoding="utf-8")


def test_build_pages_site_preserves_existing_manuals(tmp_path: Path):
    payload = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", payload)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / ".nojekyll").write_text("", encoding="utf-8")
    (docs_dir / "HANDOFF.md").write_text("# handoff", encoding="utf-8")
    (docs_dir / "OPS_RUNBOOK.md").write_text("# runbook", encoding="utf-8")
    (docs_dir / "USER_GUIDE.md").write_text("# guide", encoding="utf-8")

    build_pages_site(tmp_path)

    assert (docs_dir / "HANDOFF.md").exists()
    assert (docs_dir / "OPS_RUNBOOK.md").exists()
    assert (docs_dir / "USER_GUIDE.md").exists()
    assert (docs_dir / "index.html").exists()
    assert (docs_dir / "archives" / "2026-04-11" / "index.html").exists()


def test_build_pages_site_generates_search_index_feed_and_rss(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    older = _sample_payload("2026-04-10", "ai-x-electronics", "Anthropic")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", older)

    build_pages_site(tmp_path)

    search_index = json.loads((tmp_path / "docs" / "search-index.json").read_text(encoding="utf-8"))
    feed = json.loads((tmp_path / "docs" / "feed.json").read_text(encoding="utf-8"))
    rss = (tmp_path / "docs" / "rss.xml").read_text(encoding="utf-8")

    assert search_index["meta"]["entry_count"] == 4
    assert search_index["entries"][0]["domain"]
    assert search_index["entries"][0]["source"]
    assert "tags" in search_index["entries"][0]
    assert feed["version"] == "https://jsonfeed.org/version/1.1"
    assert len(feed["items"]) == 2
    assert "<rss" in rss
    assert "<item>" in rss
    assert "OpenAI 成为本轮最强主线" in rss


def test_build_pages_site_homepage_and_archives_are_data_driven(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    older = _sample_payload("2026-04-10", "ai-x-electronics", "Anthropic")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", older)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    archive_index = (tmp_path / "docs" / "archives" / "index.html").read_text(encoding="utf-8")
    archive_day = (tmp_path / "docs" / "archives" / "2026-04-10" / "index.html").read_text(encoding="utf-8")

    assert "情报工作台" in index_html
    assert "search-index.json" in index_html
    assert "OpenAI 发布新版本" in index_html
    assert "归档检索" in index_html
    assert "Anthropic 平台更新" in archive_day
    assert "按领域浏览" in archive_index
    assert "按来源浏览" in archive_index


def test_build_pages_site_homepage_renders_chinese_workbench_and_comparison(tmp_path: Path):
    latest = _with_comparison_brief(_sample_payload("2026-04-11", "ai-llm-agent", "OpenAI"))
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "情报工作台" in index_html
    assert "今日判断" in index_html
    assert "国内外对比" in index_html
    assert "智能体可靠性" in index_html
    assert "国内更关注模型生态和应用落地" in index_html
    assert "海外更关注沙箱、调试和运行时安全" in index_html
    assert "Briefing For AI Signals" not in index_html
    assert ">Archives<" not in index_html


def test_build_pages_site_day_page_renders_comparison_when_available(tmp_path: Path):
    latest = _with_comparison_brief(_sample_payload("2026-04-11", "ai-llm-agent", "OpenAI"))
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    day_html = (tmp_path / "docs" / "archives" / "2026-04-11" / "index.html").read_text(encoding="utf-8")

    assert "国内外对比" in day_html
    assert "智能体可靠性" in day_html


def test_build_pages_site_localizes_comparison_track_labels(tmp_path: Path):
    latest = _with_english_comparison_brief(_sample_payload("2026-04-11", "ai-llm-agent", "OpenAI"))
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "前沿 AI" in index_html
    assert "算力基础设施：仅看到海外信号" in index_html
    assert "继续跟踪 前沿 AI 的国内外同轨发布" in index_html
    assert "frontier-ai" not in index_html
    assert "compute-infra" not in index_html


def test_build_pages_site_localizes_known_mainline_titles(tmp_path: Path):
    payload = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    payload["key_points"] = [
        {
            "title": "Systematic debugging for AI agents: Introducing the AgentRx framework",
            "why_it_matters": "Agent failures need traceable diagnostics.",
        }
    ]
    _write_report_set(tmp_path, "2026-04-11", payload)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "AI 智能体系统化调试：AgentRx 框架" in index_html
    assert "Systematic debugging for AI agents" not in index_html


def test_build_pages_site_homepage_omits_comparison_when_missing(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "情报工作台" in index_html
    assert "国内外对比" not in index_html
    assert "Briefing For AI Signals" not in index_html


def test_build_pages_site_signal_cards_link_to_article_teasers(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    search_index = json.loads((tmp_path / "docs" / "search-index.json").read_text(encoding="utf-8"))
    article_html = (tmp_path / "docs" / "archives" / "2026-04-11" / "signals" / "1" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'class="article-card"' in index_html
    assert 'href="./archives/2026-04-11/signals/1/"' in index_html
    assert "阅读文章" in index_html
    assert search_index["entries"][0]["article_url"] == "archives/2026-04-11/signals/1/"
    assert "OpenAI 发布新版本" in article_html
    assert "2026.04.11" in article_html
    assert "发布" in article_html
    assert "基础设施" in article_html
    assert "ai-llm-agent" not in article_html
    assert "查看正文" in article_html
    assert "OpenAI 发布新版本，强调推理效率与稳定交付" not in article_html


def test_build_pages_site_recent_archive_cards_link_to_report_teasers(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", latest)

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    teaser_html = (tmp_path / "docs" / "archives" / "2026-04-11" / "brief" / "index.html").read_text(
        encoding="utf-8"
    )

    assert 'href="./archives/2026-04-11/brief/"' in index_html
    assert "OpenAI 成为本轮最强主线" in teaser_html
    assert "2026.04.11" in teaser_html
    assert "AI/智能体" in teaser_html
    assert "查看正文" in teaser_html
    assert "公开站需要支持长期检索与归档阅读" not in teaser_html


def test_build_pages_site_keeps_private_ops_fields_out_of_public_pages(tmp_path: Path):
    payload = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    _write_report_set(tmp_path, "2026-04-11", payload)
    (tmp_path / "data" / "state").mkdir(parents=True)
    (tmp_path / "data" / "state" / "run-status.json").write_text(
        json.dumps(
            {
                "delivery_results": {"channels": {"pushplus": {"error_type": "network"}}},
                "scheduler": {"trigger_kind": "compensation", "compensation_run": True},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    build_pages_site(tmp_path)

    public_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    search_index = (tmp_path / "docs" / "search-index.json").read_text(encoding="utf-8")

    assert "delivery_results" not in public_html
    assert "scheduler" not in public_html
    assert "error_type" not in public_html
    assert "compensation" not in search_index


def test_build_pages_site_uses_archive_folder_date_for_backfill_entries(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    backfill = _sample_payload("2026-04-11", "ai-x-electronics", "Anthropic")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-09", backfill)

    build_pages_site(tmp_path)

    archive_index = (tmp_path / "docs" / "archives" / "index.html").read_text(encoding="utf-8")
    assert "2026.04.09" in archive_index
    assert (tmp_path / "docs" / "archives" / "2026-04-09" / "index.html").exists()


def test_build_pages_site_generates_weekly_index_and_detail_pages(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    same_week = _sample_payload("2026-04-10", "ai-x-electronics", "Anthropic")
    previous_week = _sample_payload("2026-04-03", "ai-llm-agent", "DeepSeek")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", same_week)
    _write_report_set(tmp_path, "2026-04-03", previous_week)

    build_pages_site(tmp_path)

    weekly_index = (tmp_path / "docs" / "weekly" / "index.html").read_text(encoding="utf-8")
    current_week_page = (tmp_path / "docs" / "weekly" / "2026-W15" / "index.html").read_text(encoding="utf-8")
    previous_week_page = (tmp_path / "docs" / "weekly" / "2026-W14" / "index.html").read_text(encoding="utf-8")

    assert "周报" in weekly_index
    assert "2026-W15" in weekly_index
    assert "2026-W14" in weekly_index
    assert "OpenAI 成为本轮最强主线" in current_week_page
    assert "Anthropic 成为本轮最强主线" in current_week_page
    assert "OpenAI 发布新版本" in current_week_page
    assert "2026.04.11" in current_week_page
    assert "DeepSeek 成为本轮最强主线" in previous_week_page


def test_build_pages_site_generates_special_index_and_category_pages(tmp_path: Path):
    latest = _sample_payload("2026-04-11", "ai-llm-agent", "OpenAI")
    older = _sample_payload("2026-04-10", "ai-x-electronics", "Anthropic")
    _write_report_set(tmp_path, "2026-04-11", latest)
    _write_report_set(tmp_path, "2026-04-10", older)

    build_pages_site(tmp_path)

    special_index = (tmp_path / "docs" / "special" / "index.html").read_text(encoding="utf-8")
    verified_page = (tmp_path / "docs" / "special" / "verified" / "index.html").read_text(encoding="utf-8")
    risk_page = (tmp_path / "docs" / "special" / "risk-watch" / "index.html").read_text(encoding="utf-8")

    assert "专题" in special_index
    assert "已验证主线" in special_index
    assert "风险观察" in special_index
    assert "OpenAI 发布新版本" in verified_page
    assert "Anthropic 发布新版本" in verified_page
    assert "OpenAI 推出归档检索" in risk_page
    assert "Anthropic 推出归档检索" in risk_page


def test_build_pages_site_prefers_reviewed_track_when_both_exist(tmp_path: Path):
    auto_payload = _sample_payload(
        "2026-04-11",
        "ai-llm-agent",
        "OpenAI",
        publication_mode="auto",
        one_line_core="OpenAI auto judgment",
    )
    reviewed_payload = _sample_payload(
        "2026-04-11",
        "ai-llm-agent",
        "OpenAI",
        publication_mode="reviewed",
        one_line_core="OpenAI reviewed judgment",
    )

    _write_track_report_set(tmp_path, "2026-04-11", auto_payload, "auto")
    _write_track_report_set(tmp_path, "2026-04-11", reviewed_payload, "reviewed")
    (tmp_path / "data" / "reports" / "latest-summary.json").write_text(
        json.dumps(auto_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    build_pages_site(tmp_path)

    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")

    assert "OpenAI reviewed judgment" in index_html
    assert "人工复核版" in index_html


def test_build_pages_site_surfaces_review_metadata_and_emerging_specials(tmp_path: Path):
    reviewed = _sample_payload(
        "2026-04-11",
        "ai-llm-agent",
        "OpenAI",
        publication_mode="reviewed",
        reviewer="Alice",
        review_note="checked key sources",
    )
    previous = _sample_payload(
        "2026-04-10",
        "ai-llm-agent",
        "Anthropic",
        publication_mode="auto",
    )

    _write_track_report_set(tmp_path, "2026-04-11", reviewed, "reviewed")
    _write_track_report_set(tmp_path, "2026-04-10", previous, "auto")
    (tmp_path / "data" / "reports" / "latest-summary.json").write_text(
        json.dumps(reviewed, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    build_pages_site(tmp_path)

    weekly_page = (tmp_path / "docs" / "weekly" / "2026-W15" / "index.html").read_text(encoding="utf-8")
    special_index = (tmp_path / "docs" / "special" / "index.html").read_text(encoding="utf-8")
    emerging_page = (tmp_path / "docs" / "special" / "emerging" / "index.html").read_text(encoding="utf-8")

    assert "持续主线" in weekly_page
    assert "Alice" in weekly_page
    assert "人工复核版" in weekly_page
    assert "新兴主题" in special_index
    assert "OpenAI 推出归档检索" in emerging_page
    assert "Alice" in emerging_page
