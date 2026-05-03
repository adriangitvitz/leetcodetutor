from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import Problem, Statement, TutorResponse


async def import_md_files(session: AsyncSession, leetcode_dir: Path) -> int:
    if not leetcode_dir.is_dir():
        return 0

    known_slugs = set((await session.scalars(select(Problem.slug))).all())

    inserted = 0
    for md_path in sorted(leetcode_dir.glob("*.md")):
        slug = md_path.stem
        if slug not in known_slugs:
            continue
        existing = await session.get(Statement, slug)
        if existing is not None:
            continue
        session.add(Statement(slug=slug, content=md_path.read_text(encoding="utf-8")))
        inserted += 1

    if inserted:
        await session.commit()
    return inserted


async def import_cache_db(session: AsyncSession, cache_db_path: Path) -> int:
    if not cache_db_path.exists():
        return 0

    known_slugs = set((await session.scalars(select(Problem.slug))).all())
    inserted = 0

    conn = sqlite3.connect(f"file:{cache_db_path}?mode=ro", uri=True)
    try:
        try:
            rows = conn.execute(
                "SELECT slug, provider, model, persona, kind, payload, created_at "
                "FROM tutor_cache ORDER BY created_at"
            ).fetchall()
        except sqlite3.OperationalError:
            return 0  # no tutor_cache table nothing to import

        for slug, provider, model, persona, kind, payload, created_at in rows:
            if slug not in known_slugs:
                continue
            existing = await session.get(
                TutorResponse, (slug, provider, model, persona, kind)
            )
            if existing is not None:
                continue
            try:
                payload_obj = json.loads(payload) if isinstance(payload, str) else payload
            except json.JSONDecodeError:
                continue
            session.add(
                TutorResponse(
                    slug=slug,
                    provider=provider,
                    model=model,
                    persona=persona,
                    kind=kind,
                    payload=payload_obj,
                    created_at=_parse_dt(created_at),
                    refreshed_at=_parse_dt(created_at),
                )
            )
            inserted += 1
    finally:
        conn.close()

    if inserted:
        await session.commit()
    return inserted


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)
