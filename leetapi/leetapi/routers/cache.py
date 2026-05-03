from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import get_session
from ..schemas import CacheDump, CacheRow
from ..services.cache import list_recent

router = APIRouter(prefix="/cache", tags=["meta"])


@router.get("", response_model=CacheDump)
async def dump(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 200,
) -> CacheDump:
    rows = await list_recent(session, limit=limit)
    items = [
        CacheRow(
            slug=r.slug,
            provider=r.provider,
            model=r.model,
            persona=r.persona,
            kind=r.kind,
            bytes=len(str(r.payload)),
            created_at=r.created_at.isoformat(),
            refreshed_at=r.refreshed_at.isoformat(),
        )
        for r in rows
    ]
    return CacheDump(count=len(items), rows=items)
