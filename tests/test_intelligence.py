import json
from pathlib import Path

from auto_report.models.records import CollectedItem
from auto_report.pipeline.intelligence import apply_intelligence_layer


def _write_archive_payload(root_dir: Path, archive_date: str, payload: dict[str, object]) -> None:
    archive_dir = root_dir / "data" / "archives" / archive_date
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = str(payload["meta"]["generated_at"]).replace(":", "-")
    (archive_dir / f"{timestamp}-summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_apply_intelligence_layer_tracks_cross_day_memory_and_verified_lifecycle(tmp_path: Path):
    _write_archive_payload(
        tmp_path,
        "2026-04-10",
        {
            "meta": {
                "generated_at": "2026-04-10T07:00:00+08:00",
            },
            "signals": [
                {
                    "title": "OpenAI launches secure agent runtime",
                    "url": "https://openai.com/news/secure-agent-runtime",
                    "primary_domain": "ai-llm-agent",
                    "score": 2.3,
                    "evidence_count": 1,
                    "source_ids": ["openai-news"],
                    "tags": ["release"],
                }
            ],
            "analyses": [
                {
                    "title": "OpenAI launches secure agent runtime",
                    "url": "https://openai.com/news/secure-agent-runtime",
                    "primary_domain": "ai-llm-agent",
                    "confidence": "medium",
                }
            ],
        },
    )

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "OpenAI launches secure agent runtime",
                "url": "https://openai.com/news/secure-agent-runtime",
                "summary": "OpenAI expands its agent runtime with safer orchestration.",
                "primary_domain": "ai-llm-agent",
                "score": 3.1,
                "evidence_count": 2,
                "source_ids": ["openai-news", "curated-repos"],
                "tags": ["release", "runtime"],
            }
        ],
        analyses=[
            {
                "title": "OpenAI launches secure agent runtime",
                "url": "https://openai.com/news/secure-agent-runtime",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "speed vs control",
                "core_insight": "The runtime is moving from demo tooling toward production safety.",
                "confidence": "high",
            }
        ],
        diagnostics=[],
        generated_at="2026-04-11T07:00:00+08:00",
    )

    signal = result["signals"][0]
    analysis = result["analyses"][0]

    assert signal["memory"]["days_seen"] == 2
    assert signal["memory"]["first_seen"] == "2026-04-10"
    assert signal["lifecycle_state"] == "verified"
    assert signal["risk_level"] == "low"
    assert signal["enrichment"]["cross_source_count"] == 2
    assert signal["enrichment"]["source_types"] == ["official", "repo"]
    assert "cross-source" in signal["enrichment"]["verification_flags"]
    assert analysis["lifecycle_state"] == "verified"
    assert analysis["risk_level"] == "low"
    assert result["risk_level"] == "low"
    assert result["lifecycle_summary"]["verified"] == 1
    assert result["mainline_memory"][0]["title"] == "OpenAI launches secure agent runtime"


def test_apply_intelligence_layer_marks_new_high_value_single_source_topics_high_risk(tmp_path: Path):
    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Stealth startup claims universal agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "summary": "Only one community post is available so far.",
                "primary_domain": "ai-llm-agent",
                "score": 3.2,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["show-hn"],
            }
        ],
        analyses=[
            {
                "title": "Stealth startup claims universal agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "vision vs evidence",
                "core_insight": "The claim is interesting but lacks verification depth.",
                "confidence": "low",
            }
        ],
        diagnostics=["HN: fetched 59 raw, filtered to 13 relevant (min_score=10)"],
        generated_at="2026-04-11T07:00:00+08:00",
    )

    signal = result["signals"][0]

    assert signal["memory"]["days_seen"] == 1
    assert signal["lifecycle_state"] == "new"
    assert signal["risk_level"] == "high"
    assert signal["enrichment"]["source_types"] == ["community"]
    assert result["risk_level"] == "high"
    assert result["lifecycle_summary"]["new"] == 1


def test_apply_intelligence_layer_attaches_related_support_evidence_and_reduces_risk(tmp_path: Path):
    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "summary": "Community launch post",
                "primary_domain": "ai-llm-agent",
                "score": 3.3,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["show-hn"],
            }
        ],
        analyses=[
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "primary_domain": "ai-llm-agent",
                "primary_contradiction": "vision vs evidence",
                "core_insight": "Interesting launch, but needs outside corroboration.",
                "confidence": "low",
            }
        ],
        items=[
            CollectedItem(
                source_id="openai-news",
                item_id="official-1",
                title="OpenAI launches agent debugger",
                url="https://openai.com/news/agent-debugger",
                summary="Official release note for the agent debugger runtime.",
                published_at="2026-04-11T00:00:00+08:00",
                collected_at="2026-04-11T00:10:00+08:00",
                tags=["release"],
                language="en",
                metadata={},
            ),
            CollectedItem(
                source_id="curated-repos",
                item_id="repo-1",
                title="agent-debugger toolkit",
                url="https://github.com/example/agent-debugger",
                summary="Reference repository for the same debugger concept.",
                published_at="2026-04-11T00:00:00+08:00",
                collected_at="2026-04-11T00:10:00+08:00",
                tags=["repo"],
                language="en",
                metadata={},
            ),
        ],
        diagnostics=[],
        generated_at="2026-04-11T07:00:00+08:00",
    )

    signal = result["signals"][0]
    analysis = result["analyses"][0]
    support = signal["enrichment"]["support_evidence"]

    assert len(support) == 2
    assert support[0]["source_type"] == "official"
    assert support[0]["title"] == "OpenAI launches agent debugger"
    assert support[1]["source_type"] == "repo"
    assert "related-support" in signal["enrichment"]["verification_flags"]
    assert signal["risk_level"] == "medium"
    assert analysis["support_evidence"][0]["url"] == "https://openai.com/news/agent-debugger"


def test_apply_intelligence_layer_adds_external_support_evidence_only_for_high_value_topics(tmp_path: Path):
    fetched_titles: list[str] = []

    def fake_external_fetcher(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        fetched_titles.append(str(signal.get("title", "")))
        return [
            {
                "source_id": "arxiv-search",
                "source_type": "paper",
                "title": "Agent Debugger for Tool-Using Models",
                "url": "https://arxiv.org/abs/2604.12345",
                "summary": "Paper describing debugger-style agent tracing.",
                "evidence_scope": "external",
            }
        ]

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "summary": "Community launch post",
                "primary_domain": "ai-llm-agent",
                "score": 3.3,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["show-hn"],
            },
            {
                "title": "Minor SDK patch",
                "url": "https://example.com/sdk-patch",
                "summary": "Routine patch note",
                "primary_domain": "ai-llm-agent",
                "score": 1.5,
                "evidence_count": 1,
                "source_ids": ["openai-news"],
                "tags": ["patch"],
            },
        ],
        analyses=[
            {
                "title": "Launch HN: Agent debugger",
                "url": "https://news.ycombinator.com/item?id=1",
                "primary_domain": "ai-llm-agent",
                "confidence": "low",
            },
            {
                "title": "Minor SDK patch",
                "url": "https://example.com/sdk-patch",
                "primary_domain": "ai-llm-agent",
                "confidence": "medium",
            },
        ],
        diagnostics=[],
        generated_at="2026-04-11T07:00:00+08:00",
        external_enrichment_fetcher=fake_external_fetcher,
    )

    assert fetched_titles == ["Launch HN: Agent debugger"]
    support = result["signals"][0]["enrichment"]["support_evidence"]
    assert support[0]["source_type"] == "paper"
    assert support[0]["evidence_scope"] == "external"
    assert "external-support" in result["signals"][0]["enrichment"]["verification_flags"]
    assert result["analyses"][0]["support_evidence"][0]["url"] == "https://arxiv.org/abs/2604.12345"
    assert result["signals"][1]["enrichment"]["support_evidence"] == []


def test_apply_intelligence_layer_limits_external_enrichment_attempts_to_top_n_high_value_topics(tmp_path: Path):
    fetched_titles: list[str] = []

    def fake_external_fetcher(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        fetched_titles.append(str(signal.get("title", "")))
        return [
            {
                "source_id": "arxiv-search",
                "source_type": "paper",
                "title": f"Support for {signal['title']}",
                "url": f"https://example.com/{len(fetched_titles)}",
                "summary": "External support",
                "evidence_scope": "external",
            }
        ]

    apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Topic A",
                "url": "https://example.com/a",
                "summary": "High value A",
                "primary_domain": "ai-llm-agent",
                "score": 3.6,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic B",
                "url": "https://example.com/b",
                "summary": "High value B",
                "primary_domain": "ai-llm-agent",
                "score": 3.4,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic C",
                "url": "https://example.com/c",
                "summary": "High value C",
                "primary_domain": "ai-llm-agent",
                "score": 3.1,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
        ],
        analyses=[
            {"title": "Topic A", "url": "https://example.com/a", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic B", "url": "https://example.com/b", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic C", "url": "https://example.com/c", "primary_domain": "ai-llm-agent", "confidence": "low"},
        ],
        diagnostics=[],
        generated_at="2026-04-11T07:00:00+08:00",
        external_enrichment_fetcher=fake_external_fetcher,
        external_enrichment_max_signals=2,
    )

    assert fetched_titles == ["Topic A", "Topic B"]


def test_apply_intelligence_layer_tracks_external_enrichment_runtime_metrics(tmp_path: Path):
    fetched_titles: list[str] = []

    def fake_external_fetcher(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        fetched_titles.append(str(signal.get("title", "")))
        if signal["title"] == "Topic A":
            return [
                {
                    "source_id": "arxiv-search",
                    "source_type": "paper",
                    "title": "Support for Topic A",
                    "url": "https://example.com/a-paper",
                    "summary": "paper support",
                    "evidence_scope": "external",
                }
            ]
        return []

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Topic A",
                "url": "https://example.com/a",
                "summary": "High value A",
                "primary_domain": "ai-llm-agent",
                "score": 3.6,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic B",
                "url": "https://example.com/b",
                "summary": "High value B",
                "primary_domain": "ai-llm-agent",
                "score": 3.5,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic C",
                "url": "https://example.com/c",
                "summary": "Below threshold C",
                "primary_domain": "ai-llm-agent",
                "score": 2.0,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
        ],
        analyses=[
            {"title": "Topic A", "url": "https://example.com/a", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic B", "url": "https://example.com/b", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic C", "url": "https://example.com/c", "primary_domain": "ai-llm-agent", "confidence": "medium"},
        ],
        diagnostics=[],
        generated_at="2026-04-12T07:00:00+08:00",
        external_enrichment_fetcher=fake_external_fetcher,
        external_enrichment_max_signals=2,
    )

    metrics = result["external_enrichment"]

    assert fetched_titles == ["Topic A", "Topic B"]
    assert metrics["enabled"] is True
    assert metrics["max_signals"] == 2
    assert metrics["attempted"] == 2
    assert metrics["succeeded"] == 1
    assert metrics["failed"] == 1
    assert metrics["skipped"] == 1
    assert metrics["budget_used"] == 2
    assert metrics["success_rate"] == 0.5
    assert metrics["circuit_open"] is False
    assert "empty-result: Topic B" in metrics["reasons"]
    assert "below-threshold: Topic C" in metrics["reasons"]


def test_apply_intelligence_layer_opens_circuit_after_two_consecutive_failures(tmp_path: Path):
    fetched_titles: list[str] = []

    def always_fail(root_dir: Path, signal: dict[str, object]) -> list[dict[str, object]]:
        fetched_titles.append(str(signal.get("title", "")))
        return []

    result = apply_intelligence_layer(
        root_dir=tmp_path,
        signals=[
            {
                "title": "Topic A",
                "url": "https://example.com/a",
                "summary": "High value A",
                "primary_domain": "ai-llm-agent",
                "score": 3.8,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic B",
                "url": "https://example.com/b",
                "summary": "High value B",
                "primary_domain": "ai-llm-agent",
                "score": 3.7,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
            {
                "title": "Topic C",
                "url": "https://example.com/c",
                "summary": "High value C",
                "primary_domain": "ai-llm-agent",
                "score": 3.6,
                "evidence_count": 1,
                "source_ids": ["hacker-news"],
                "tags": ["agent"],
            },
        ],
        analyses=[
            {"title": "Topic A", "url": "https://example.com/a", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic B", "url": "https://example.com/b", "primary_domain": "ai-llm-agent", "confidence": "low"},
            {"title": "Topic C", "url": "https://example.com/c", "primary_domain": "ai-llm-agent", "confidence": "low"},
        ],
        diagnostics=[],
        generated_at="2026-04-12T07:00:00+08:00",
        external_enrichment_fetcher=always_fail,
        external_enrichment_max_signals=3,
    )

    metrics = result["external_enrichment"]

    assert fetched_titles == ["Topic A", "Topic B"]
    assert metrics["attempted"] == 2
    assert metrics["failed"] == 2
    assert metrics["skipped"] == 1
    assert metrics["budget_used"] == 2
    assert metrics["circuit_open"] is True
    assert "empty-result: Topic A" in metrics["reasons"]
    assert "empty-result: Topic B" in metrics["reasons"]
    assert "circuit-open: Topic C" in metrics["reasons"]
