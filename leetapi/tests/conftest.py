"""Shared pytest fixtures.

Each test gets a brand-new in-memory SQLite database via a fresh AsyncEngine.
Tests never share state.

Usage:
    async def test_something(client, session):
        r = await client.get("/health")
        assert r.status_code == 200
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

# Force test config BEFORE any leetapi imports so Settings picks it up.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("LLM_PROVIDER", "openrouter")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from leetapi import db as db_module
from leetapi import models  # noqa: F401  — populate metadata
from leetapi.config import Settings, get_settings
from leetapi.main import create_app


@pytest_asyncio.fixture
async def engine(tmp_path) -> AsyncIterator[AsyncEngine]:
    """Per-test SQLite engine backed by a tempfile.

    Tempfile (vs `:memory:`) lets multiple concurrent connections coexist on
    the same DB, which is required for correctly modeling the prod behavior
    of cache lookups + dedup + concurrent saves under FastAPI's per-request
    sessions. The file is auto-removed when pytest cleans `tmp_path`."""
    db_path = tmp_path / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with AsyncSession(engine) as s:
        yield s


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """ASGI in-process httpx client. The app's `get_session` and
    `get_async_engine` deps are patched to use the test engine."""
    app = create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine) as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[db_module.get_session] = _override_session

    # Also point the module-level engine accessor at our test engine so any
    # code that calls get_async_engine() directly (outside of FastAPI deps)
    # sees the same DB.
    db_module._async_engine = engine  # type: ignore[attr-defined]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    db_module.reset_engines()
    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest_asyncio.fixture
def settings() -> Settings:
    """Return the active Settings (already overridden by env vars at top of file)."""
    return get_settings()


@pytest_asyncio.fixture(autouse=True)
async def _reset_module_state():
    """Process-local dedup/lock dicts persist across tests. Clear before AND
    after each test so concurrent tests don't see each other's stale in-flight
    tasks (which still hold references to the previous test's session)."""
    import asyncio

    from leetapi.services import cache as cache_module
    from leetapi.services import leetcode as leetcode_module

    async def _flush() -> None:
        for task in list(cache_module._inflight.values()):
            if not task.done():
                task.cancel()
        cache_module._inflight.clear()
        leetcode_module._statement_locks.clear()
        # Yield so cancellations actually process before the next code runs.
        await asyncio.sleep(0)

    await _flush()
    yield
    await _flush()


# Path to the tiny 3-company CSV fixture used by /problems integration tests.
from pathlib import Path  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "problems_csv"


@pytest_asyncio.fixture
async def loaded_catalog(client, engine) -> AsyncClient:
    """Pre-populates the test DB with the 3-company fixture catalog
    (3 problems, 3 companies, 5 problem_companies links)."""
    from leetapi.services.importer import ingest_csvs

    async with AsyncSession(engine) as session:
        await ingest_csvs(session, FIXTURES_DIR)
    return client
