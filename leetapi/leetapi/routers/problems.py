from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import and_, desc, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import get_session
from ..models import Problem, ProblemCompany
from ..schemas import ProblemList, ProblemSummary
from ..services.leetcode import ensure_statement, parse_statement

router = APIRouter(prefix="/problems", tags=["problems"])

SortField = Literal["company_count", "mean_frequency", "acceptance_rate", "title", "difficulty"]
Order = Literal["asc", "desc"]


def _split_csv(raw: str | None) -> list[str]:
    """`"a, b , c"` → `["a", "b", "c"]`. Empty / None → []."""
    if not raw:
        return []
    return [s.strip() for s in raw.split(",") if s.strip()]


@router.get("", response_model=ProblemList)
async def list_problems(
    session: Annotated[AsyncSession, Depends(get_session)],
    topics: str | None = Query(None, description="Comma list. Match any (substring on `topics` column)."),
    topics_all: str | None = Query(None, description="Comma list. Must contain ALL listed topics."),
    difficulty: str | None = Query(None, description="Comma list of EASY|MEDIUM|HARD."),
    company: str | None = Query(None, description="Single company. JOIN problem_companies."),
    companies_all: str | None = Query(None, description="Comma list. Asked by ALL listed companies."),
    min_company_count: int | None = Query(None, ge=0),
    min_frequency: float | None = Query(None, ge=0),
    max_acceptance: float | None = Query(None, ge=0, le=1),
    min_acceptance: float | None = Query(None, ge=0, le=1),
    title_contains: str | None = Query(None, description="LIKE on title (case-insensitive)."),
    slug: str | None = Query(None, description="Comma list of specific slugs."),
    sort: SortField = "company_count",
    order: Order = "desc",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ProblemList:
    where = []

    any_topics = _split_csv(topics)
    if any_topics:
        where.append(or_(*[func.lower(Problem.topics).like(f"%{n.lower()}%") for n in any_topics]))
    for needle in _split_csv(topics_all):
        where.append(func.lower(Problem.topics).like(f"%{needle.lower()}%"))

    diffs = _split_csv(difficulty)
    if diffs:
        where.append(Problem.difficulty.in_([d.upper() for d in diffs]))

    if min_company_count is not None:
        where.append(Problem.company_count >= min_company_count)
    if min_frequency is not None:
        where.append(Problem.mean_frequency >= min_frequency)
    if max_acceptance is not None:
        where.append(Problem.acceptance_rate <= max_acceptance)
    if min_acceptance is not None:
        where.append(Problem.acceptance_rate >= min_acceptance)

    if title_contains:
        where.append(func.lower(Problem.title).like(f"%{title_contains.lower()}%"))

    slugs = _split_csv(slug)
    if slugs:
        where.append(Problem.slug.in_(slugs))

    if company:
        where.append(
            Problem.slug.in_(
                select(ProblemCompany.slug).where(ProblemCompany.company == company)
            )
        )

    companies_required = _split_csv(companies_all)
    if companies_required:
        sub = (
            select(ProblemCompany.slug)
            .where(ProblemCompany.company.in_(companies_required))
            .group_by(ProblemCompany.slug)
            .having(func.count(func.distinct(ProblemCompany.company)) == len(companies_required))
        )
        where.append(Problem.slug.in_(sub))

    where_clause = and_(*where) if where else None

    count_stmt = select(func.count()).select_from(Problem)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
    total = (await session.execute(count_stmt)).scalar_one()

    sort_col = {
        "company_count": Problem.company_count,
        "mean_frequency": Problem.mean_frequency,
        "acceptance_rate": Problem.acceptance_rate,
        "title": Problem.title,
        "difficulty": Problem.difficulty,
    }[sort]
    sort_expr = desc(sort_col) if order == "desc" else sort_col.asc()

    page_stmt = select(Problem)
    if where_clause is not None:
        page_stmt = page_stmt.where(where_clause)
    page_stmt = page_stmt.order_by(sort_expr, Problem.slug.asc()).offset(offset).limit(limit)
    page_rows = (await session.scalars(page_stmt)).all()

    items = await _attach_companies(session, page_rows)
    return ProblemList(total=total, items=items)


@router.get("/{slug}", response_model=ProblemSummary)
async def get_problem(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProblemSummary:
    row = await session.get(Problem, slug)
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown problem slug: {slug}")
    [item] = await _attach_companies(session, [row])
    return item


@router.get("/{slug}/statement")
async def get_statement(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    format: Literal["json", "markdown"] = Query("json"),
):
    if await session.get(Problem, slug) is None:
        raise HTTPException(status_code=404, detail=f"unknown problem slug: {slug}")

    statement = await ensure_statement(session, slug)

    if format == "markdown":
        return PlainTextResponse(content=statement.content, media_type="text/markdown")

    return parse_statement(statement.content)

async def _attach_companies(session: AsyncSession, rows: list[Problem]) -> list[ProblemSummary]:
    """One round-trip to fetch company lists for all returned problems."""
    if not rows:
        return []
    slugs = [r.slug for r in rows]
    link_stmt = (
        select(ProblemCompany.slug, ProblemCompany.company)
        .where(ProblemCompany.slug.in_(slugs))
        .order_by(ProblemCompany.slug, ProblemCompany.company)
    )
    by_slug: dict[str, list[str]] = {s: [] for s in slugs}
    for slug, company in (await session.execute(link_stmt)).all():
        by_slug[slug].append(company)

    return [
        ProblemSummary(
            slug=r.slug,
            title=r.title,
            difficulty=r.difficulty,
            topics=r.topics,
            company_count=r.company_count,
            mean_frequency=r.mean_frequency,
            max_frequency=r.max_frequency,
            acceptance_rate=r.acceptance_rate,
            link=r.link,
            companies=by_slug.get(r.slug, []),
        )
        for r in rows
    ]
