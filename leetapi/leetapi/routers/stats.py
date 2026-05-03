from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import get_session
from ..schemas import StatsResponse, TopProblemEntry, TopTopicEntry
from ..services.stats import global_stats

router = APIRouter(prefix="/stats", tags=["catalog"])


@router.get("", response_model=StatsResponse)
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
    top_problems_limit: int = Query(30, ge=1, le=200),
) -> StatsResponse:
    s = await global_stats(session, top_problems_limit=top_problems_limit)
    return StatsResponse(
        top_problems=[
            TopProblemEntry(
                slug=p.slug,
                title=p.title,
                difficulty=p.difficulty,
                topics=p.topics,
                link=p.link,
                company_count=p.company_count,
                mean_frequency=p.mean_frequency,
                score=p.score,
            )
            for p in s.top_problems
        ],
        top_topics=[TopTopicEntry(name=t.name, score=t.score) for t in s.top_topics],
        difficulty_mix=s.difficulty_mix,
    )
