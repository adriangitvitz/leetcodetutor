from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import get_session
from ..models import Problem
from ..schemas import (
    CompleteRequest,
    CompleteResponse,
    ExplainRequest,
    ExplainResponse,
)
from ..services.cache import (
    dedupe,
    dedupe_key,
    delete_response,
    get_response,
    save_response,
)
from ..services.leetcode import ensure_statement
from ..services.llm import complete
from ..services.personas import is_valid_persona
from ..services.prompts import ProblemContext
from ..services.tutor import generate_socratic, generate_teacher

router = APIRouter(prefix="/tutor", tags=["tutor"])

VALID_KINDS = frozenset({"teacher", "socratic"})


def _request_id() -> str:
    return secrets.token_hex(3)


@router.post("/{slug}/explain", response_model=ExplainResponse)
async def explain(
    slug: str,
    body: ExplainRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExplainResponse:
    if body.kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail="kind must be 'teacher' or 'socratic'")
    if not is_valid_persona(body.persona):
        raise HTTPException(status_code=400, detail=f"unknown persona: {body.persona!r}")
    if not body.provider or not body.model:
        raise HTTPException(status_code=400, detail="provider and model are required")

    problem = await session.get(Problem, slug)
    if problem is None:
        raise HTTPException(status_code=404, detail=f"unknown problem slug: {slug}")
    p_title = problem.title
    p_difficulty = problem.difficulty
    p_topics = problem.topics

    rid = _request_id()
    cache_kwargs = dict(
        slug=slug,
        provider=body.provider,
        model=body.model,
        persona=body.persona,
        kind=body.kind,
    )

    if body.force:
        await delete_response(session, **cache_kwargs)

    cached = await get_response(session, **cache_kwargs)
    if cached is not None:
        return ExplainResponse(payload=cached.payload, cached=True, request_id=rid)

    statement = await ensure_statement(session, slug)
    ctx = ProblemContext(
        title=p_title,
        difficulty=p_difficulty,
        topics=p_topics,
        statement=statement.content,
    )

    async def _generate_and_save() -> dict:
        recheck = await get_response(session, **cache_kwargs)
        if recheck is not None:
            return recheck.payload
        if body.kind == "teacher":
            payload = await generate_teacher(
                persona_key=body.persona,  # type: ignore[arg-type]
                ctx=ctx,
                provider=body.provider,
                model=body.model,
            )
        else:
            payload = await generate_socratic(
                persona_key=body.persona,  # type: ignore[arg-type]
                ctx=ctx,
                provider=body.provider,
                model=body.model,
            )
        await save_response(session, payload=payload, request_id=rid, **cache_kwargs)
        return payload

    payload = await dedupe(dedupe_key(**cache_kwargs), _generate_and_save)
    return ExplainResponse(payload=payload, cached=False, request_id=rid)


@router.post("/complete", response_model=CompleteResponse)
async def complete_chat(
    body: CompleteRequest,
    session: Annotated[AsyncSession, Depends(get_session)],  # unused — kept for symmetry
) -> CompleteResponse:
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages[] required")

    rid = _request_id()
    provider_name = body.provider or "openrouter"
    text = await complete(
        [m.model_dump() for m in body.messages],
        provider=provider_name,
        model=body.model,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
    )
    return CompleteResponse(
        text=text,
        provider=provider_name,
        model=body.model or "(provider default)",
        request_id=rid,
    )
