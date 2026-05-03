from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from leetapi.models import TutorResponse
from ..models import TutorResponse


T = TypeVar("T")

async def get_response(
    session: AsyncSession,
    *,
    slug: str,
    provider: str,
    model: str,
    persona: str,
    kind: str,
) -> type[TutorResponse] | None:
    return await session.get(
        TutorResponse, (slug, provider, model, persona, kind)
    )


async def save_response(
    session: AsyncSession,
    *,
    slug: str,
    provider: str,
    model: str,
    persona: str,
    kind: str,
    payload: dict,
    request_id: str | None = None,
) -> type[TutorResponse] | TutorResponse:
    existing = await get_response(
        session, slug=slug, provider=provider, model=model, persona=persona, kind=kind
    )
    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.payload = payload
        existing.refreshed_at = now
        existing.request_id = request_id
        await session.commit()
        await session.refresh(existing)
        return existing
    row = TutorResponse(
        slug=slug,
        provider=provider,
        model=model,
        persona=persona,
        kind=kind,
        payload=payload,
        request_id=request_id,
    )
    session.add(row)
    try:
        await session.commit()
        await session.refresh(row)
        return row
    except IntegrityError:
        await session.rollback()
        existing = await get_response(
            session, slug=slug, provider=provider, model=model,
            persona=persona, kind=kind,
        )
        if existing is None:  # pragma: no cover
            raise
        existing.payload = payload
        existing.refreshed_at = now
        existing.request_id = request_id
        await session.commit()
        await session.refresh(existing)
        return existing


async def delete_response(
    session: AsyncSession,
    *,
    slug: str,
    provider: str,
    model: str,
    persona: str,
    kind: str,
) -> bool:
    row = await get_response(
        session, slug=slug, provider=provider, model=model, persona=persona, kind=kind
    )
    if row is None:
        return False
    await session.delete(row)
    await session.commit()
    return True


async def list_recent(session: AsyncSession, limit: int = 200) -> list[TutorResponse]:
    stmt = select(TutorResponse).order_by(TutorResponse.created_at.desc()).limit(limit)
    rows = (await session.scalars(stmt)).all()
    return list(rows)

_inflight: dict[str, asyncio.Task] = {}


def dedupe_key(*, slug: str, provider: str, model: str, persona: str, kind: str) -> str:
    return f"{slug}|{provider}|{model}|{persona}|{kind}"


async def dedupe(key: str, fn: Callable[[], Awaitable[T]]) -> T:
    existing = _inflight.get(key)
    if existing is not None and not existing.done():
        return await asyncio.shield(existing)

    async def _wrap() -> T:
        try:
            return await fn()
        finally:
            if _inflight.get(key) is task:
                _inflight.pop(key, None)

    task: asyncio.Task = asyncio.create_task(_wrap())
    _inflight[key] = task
    return await asyncio.shield(task)
