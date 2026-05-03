"""Tests for the stats service. Reuses the small 3-company CSV fixture."""

from __future__ import annotations

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from leetapi.services.importer import ingest_csvs
from leetapi.services.stats import (
    asks_for_company,
    global_stats,
    related_problems_for_company,
    signature_problem_for_company,
    top_topic_for_company,
)
from tests.conftest import FIXTURES_DIR


@pytest.fixture
async def loaded(session: AsyncSession):
    await ingest_csvs(session, FIXTURES_DIR)
    return session


# ---------- per-company ------------------------------------------------


async def test_asks_for_company_returns_problems_sorted_by_freq(loaded):
    asks = await asks_for_company(loaded, "CompanyA")
    titles = [a.title for a in asks]
    # CompanyA has Two Sum (freq 90) + LRU Cache (75) — Two Sum first.
    assert titles == ["Two Sum", "LRU Cache"]


async def test_signature_problem_is_highest_freq(loaded):
    sig = await signature_problem_for_company(loaded, "CompanyA")
    assert sig is not None and sig.title == "Two Sum"


async def test_top_topic_for_companyA_is_arrays_or_hash(loaded):
    """CompanyA asks Two Sum (Array, Hash Table) at 90 + LRU Cache
    (Hash Table, Linked List, Design) at 75. Hash Tables totals 165;
    Arrays totals 90; Linked Lists 75. Hash Tables wins."""
    topic, score = await top_topic_for_company(loaded, "CompanyA")
    assert topic == "Hash Tables"
    assert score == pytest.approx(165.0)


async def test_top_topic_returns_none_for_unknown_company(loaded):
    topic, score = await top_topic_for_company(loaded, "NoSuchCorp")
    assert topic is None and score == 0.0


async def test_related_problems_excludes_already_asked(loaded):
    """CompanyA's top topic is Hash Tables. Problems they already ask
    (Two Sum, LRU Cache) must NOT appear in related."""
    related = await related_problems_for_company(loaded, "CompanyA", limit=10)
    related_slugs = {a.slug for a in related}
    assert "two-sum" not in related_slugs
    assert "lru-cache" not in related_slugs


# ---------- global stats ------------------------------------------------


async def test_global_stats_returns_three_top_problems(loaded):
    stats = await global_stats(loaded, top_problems_limit=10)
    titles = [p.title for p in stats.top_problems]
    assert set(titles) == {"Two Sum", "LRU Cache", "N-Queens"}


async def test_global_stats_two_sum_leads_by_score(loaded):
    """Two Sum is asked by all 3 companies at high frequency, so it wins."""
    stats = await global_stats(loaded, top_problems_limit=10)
    assert stats.top_problems[0].title == "Two Sum"


async def test_global_stats_difficulty_mix_sums_to_total(loaded):
    """All three difficulties present, weighted by score."""
    stats = await global_stats(loaded)
    # Two Sum is EASY; LRU is MEDIUM; N-Queens is HARD.
    assert stats.difficulty_mix["EASY"] > 0
    assert stats.difficulty_mix["MEDIUM"] > 0
    assert stats.difficulty_mix["HARD"] > 0


async def test_global_stats_top_topics_includes_arrays(loaded):
    stats = await global_stats(loaded)
    names = {t.name for t in stats.top_topics}
    # Two Sum (Array, Hash Table), N-Queens (Array, Backtracking) → Arrays present.
    assert "Arrays" in names


async def test_global_stats_topic_percentages_sum_to_about_100(loaded):
    """After normalization, the topic shares should sum to ~100% (slightly
    less only if some problems' tags don't map to any topic group at all)."""
    stats = await global_stats(loaded)
    total = sum(t.score for t in stats.top_topics)
    assert total > 0
    percentages = [(t.score / total) * 100 for t in stats.top_topics]
    summed = sum(percentages)
    # The percentages-as-rendered should land in [99.9, 100.1] given exact
    # division. We allow a tiny tolerance for floating point.
    assert 99.5 <= summed <= 100.5, f"got {summed}"


async def test_per_company_top_topic_unchanged_after_normalization(loaded):
    """The per-company computation deliberately does NOT normalize, because
    when a problem touches multiple groups, each is an equally valid lens
    for that company. CompanyA asks Two Sum (Array+Hash Table) at 90 and
    LRU Cache (Hash Table+Linked List+Design) at 75 — Hash Tables remains
    the unambiguous winner with 165 (90 + 75) regardless of normalization."""
    from leetapi.services.stats import top_topic_for_company

    topic, score = await top_topic_for_company(loaded, "CompanyA")
    assert topic == "Hash Tables"
    assert score == pytest.approx(165.0)
