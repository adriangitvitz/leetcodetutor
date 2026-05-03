from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import cache as cache_router
from .routers import companies as companies_router
from .routers import models as models_router
from .routers import problems as problems_router
from .routers import stats as stats_router
from .routers import tutor as tutor_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="leetapi",
        description="LeetCode tutor service. See /docs for the agent-facing schema.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(problems_router.router)
    app.include_router(companies_router.router)
    app.include_router(stats_router.router)
    app.include_router(tutor_router.router)
    app.include_router(models_router.router)
    app.include_router(cache_router.router)

    return app


app = create_app()
