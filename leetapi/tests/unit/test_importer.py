"""Importer unit tests — TDD targets for `services/importer.py`.

Three companies in the fixture:
- CompanyA: Two Sum (freq 90), LRU Cache (freq 75)
- CompanyB: Two Sum (freq 80), N-Queens   (freq 60)
- CompanyC: Two Sum (freq 100, listed twice — must be deduped)

After ingest:
- 3 distinct problems
- 3 companies
- 4 problem_companies rows (dedup of CompanyC's repeat)
- two-sum has company_count=3, mean_frequency=(90+80+100)/3=90.0
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlmodel.ext.asyncio.session import AsyncSession

from leetapi.models import Company, Problem, ProblemCompany
from leetapi.services.importer import aggregate, ingest_csvs

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "problems_csv"


# ---------- pure aggregation (no DB) ----------------------------------------


def test_aggregate_produces_one_row_per_link():
    agg = aggregate(FIXTURES)
    by_slug = {p.slug: p for p in agg.problems}
    assert set(by_slug) == {"two-sum", "lru-cache", "n-queens"}


def test_aggregate_computes_company_count():
    agg = aggregate(FIXTURES)
    by_slug = {p.slug: p for p in agg.problems}
    assert by_slug["two-sum"].company_count == 3
    assert by_slug["lru-cache"].company_count == 1
    assert by_slug["n-queens"].company_count == 1


def test_aggregate_computes_mean_frequency():
    agg = aggregate(FIXTURES)
    by_slug = {p.slug: p for p in agg.problems}
    # CompanyA=90, CompanyB=80, CompanyC=100 → mean = 90.0
    assert by_slug["two-sum"].mean_frequency == pytest.approx(90.0)


def test_aggregate_dedupes_repeated_rows_within_one_company():
    """CompanyC lists Two Sum twice; the (slug, company) link should be one."""
    agg = aggregate(FIXTURES)
    company_c_links = [
        link for link in agg.links
        if link.company == "CompanyC" and link.slug == "two-sum"
    ]
    assert len(company_c_links) == 1


def test_aggregate_emits_one_company_row_per_directory():
    agg = aggregate(FIXTURES)
    assert {c.name for c in agg.companies} == {"CompanyA", "CompanyB", "CompanyC"}


# ---------- DB ingest --------------------------------------------------------


async def test_ingest_writes_all_three_tables(session: AsyncSession):
    await ingest_csvs(session, FIXTURES)

    problems = (await session.exec(select(Problem))).all()
    companies = (await session.exec(select(Company))).all()
    links = (await session.exec(select(ProblemCompany))).all()

    assert len(problems) == 3
    assert len(companies) == 3
    # 3 for two-sum (one per company) + LRU/A + N-Queens/B = 5
    assert len(links) == 5


async def test_ingest_is_idempotent(session: AsyncSession):
    """Running ingest twice yields the same row counts (no dupes, no growth)."""
    await ingest_csvs(session, FIXTURES)
    counts_first = await _table_counts(session)

    await ingest_csvs(session, FIXTURES)
    counts_second = await _table_counts(session)

    assert counts_first == counts_second


async def test_ingest_preserves_tutor_responses_on_re_run(session: AsyncSession):
    """A 2nd ingest must NOT cascade-delete existing tutor_responses."""
    from leetapi.models import TutorResponse

    await ingest_csvs(session, FIXTURES)
    session.add(TutorResponse(
        slug="two-sum",
        provider="openrouter",
        model="anthropic/claude-sonnet-4.5",
        persona="scholar",
        kind="teacher",
        payload={"plain": "test"},
    ))
    await session.commit()

    await ingest_csvs(session, FIXTURES)

    # `scalars()` returns ORM instances regardless of session state.
    rows = (await session.scalars(select(TutorResponse))).all()
    assert len(rows) == 1
    assert rows[0].payload == {"plain": "test"}
    assert rows[0].persona == "scholar"


async def _table_counts(session: AsyncSession) -> dict[str, int]:
    counts = {}
    for table in ("problems", "companies", "problem_companies"):
        result = await session.exec(text(f"SELECT count(*) FROM {table}"))  # type: ignore[arg-type]
        counts[table] = result.one()[0]
    return counts
