from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from .config import get_settings
from . import models  # noqa: F401

_async_engine: AsyncEngine | None = None
_sync_engine: Engine | None = None


def get_async_engine() -> AsyncEngine | None:
    global _async_engine
    if _async_engine is None:
        url = get_settings().database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _async_engine = create_async_engine(url, connect_args=connect_args, future=True)
    return _async_engine


def get_sync_engine() -> Engine | None:
    global _sync_engine
    if _sync_engine is None:
        url = get_settings().sync_database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _sync_engine = create_engine(url, connect_args=connect_args, future=True)
    return _sync_engine


async def get_session() -> AsyncIterator[AsyncSession]:
    engine = get_async_engine()
    async with SQLModelAsyncSession(engine) as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


def reset_engines() -> None:
    global _async_engine, _sync_engine
    _async_engine = None
    _sync_engine = None
