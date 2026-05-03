from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import get_session
from ..models import Company, ProblemCompany
from ..schemas import (
    AskEntry,
    CompanyDetail,
    CompanyEntry,
    CompanyList,
)
from ..services.stats import (
    asks_for_company,
    related_problems_for_company,
    signature_problem_for_company,
    top_topic_for_company,
)

router = APIRouter(prefix="/companies", tags=["catalog"])


@router.get("", response_model=CompanyList)
async def list_companies(
    session: Annotated[AsyncSession, Depends(get_session)],
    with_topics: bool = Query(False, description="Include top_topic + signature for each company."),
    limit: int = Query(0, ge=0, le=1000, description="0 = no limit."),
) -> CompanyList:
    stmt = (
        select(Company.name, func.count(ProblemCompany.slug).label("n"))
        .outerjoin(ProblemCompany, ProblemCompany.company == Company.name)
        .group_by(Company.name)
        .order_by(func.count(ProblemCompany.slug).desc(), Company.name.asc())
    )
    rows = (await session.execute(stmt)).all()
    if limit:
        rows = rows[:limit]

    items: list[CompanyEntry] = []
    for name, n in rows:
        entry = CompanyEntry(name=name, problem_count=n)
        if with_topics and n > 0:
            topic, score = await top_topic_for_company(session, name)
            sig = await signature_problem_for_company(session, name)
            entry.top_topic = topic
            entry.top_topic_score = score
            if sig is not None:
                entry.signature_slug = sig.slug
                entry.signature_title = sig.title
        items.append(entry)
    return CompanyList(total=len(items), items=items)


@router.get("/{name}", response_model=CompanyDetail)
async def get_company(
    name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CompanyDetail:
    if await session.get(Company, name) is None:
        raise HTTPException(status_code=404, detail=f"unknown company: {name!r}")

    asks = await asks_for_company(session, name)
    topic, score = await top_topic_for_company(session, name)
    avg = sum(a.frequency for a in asks) / len(asks) if asks else 0.0

    return CompanyDetail(
        name=name,
        total_problems=len(asks),
        top_topic=topic,
        top_topic_score=score,
        avg_frequency=avg,
        asks=[
            AskEntry(
                slug=a.slug,
                title=a.title,
                difficulty=a.difficulty,
                topics=a.topics,
                link=a.link,
                frequency=a.frequency,
            )
            for a in asks
        ],
    )


@router.get("/{name}/related", response_model=list[AskEntry])
async def related_problems(
    name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(8, ge=1, le=50),
) -> list[AskEntry]:
    if await session.get(Company, name) is None:
        raise HTTPException(status_code=404, detail=f"unknown company: {name!r}")

    related = await related_problems_for_company(session, name, limit=limit)
    return [
        AskEntry(
            slug=r.slug,
            title=r.title,
            difficulty=r.difficulty,
            topics=r.topics,
            link=r.link,
            frequency=r.frequency,
        )
        for r in related
    ]
