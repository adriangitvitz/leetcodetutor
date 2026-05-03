from __future__ import annotations

from .llm import complete_json_with_retry
from .personas import PERSONAS, PersonaKey
from .prompts import (
    ProblemContext,
    socratic_system_prompt,
    socratic_user_prompt,
    teacher_system_prompt,
    teacher_user_prompt,
)

def is_teacher_payload(x: object) -> bool:
    if not isinstance(x, dict):
        return False
    if not all(isinstance(x.get(k), str) for k in ("plain", "aha", "strategy", "code")):
        return False
    cx = x.get("complexity")
    if not isinstance(cx, dict):
        return False
    return all(isinstance(cx.get(k), str) for k in ("time", "space", "tdesc", "sdesc"))


def is_socratic_payload(x: object) -> bool:
    if not isinstance(x, dict):
        return False
    qs = x.get("questions")
    if not isinstance(qs, list) or not qs:
        return False
    return all(
        isinstance(q, dict)
        and isinstance(q.get("q"), str)
        and isinstance(q.get("hint"), str)
        for q in qs
    )

async def generate_teacher(
    *,
    persona_key: PersonaKey,
    ctx: ProblemContext,
    provider: str,
    model: str,
) -> dict:
    persona = PERSONAS[persona_key]
    return await complete_json_with_retry(
        [
            {"role": "system", "content": teacher_system_prompt(persona)},
            {"role": "user", "content": teacher_user_prompt(ctx)},
        ],
        provider=provider,
        model=model,
        validate=is_teacher_payload,
        schema_name="teacher",
        max_tokens=1800,
        temperature=0.4,
    )


async def generate_socratic(
    *,
    persona_key: PersonaKey,
    ctx: ProblemContext,
    provider: str,
    model: str,
) -> dict:
    persona = PERSONAS[persona_key]
    return await complete_json_with_retry(
        [
            {"role": "system", "content": socratic_system_prompt(persona)},
            {"role": "user", "content": socratic_user_prompt(ctx)},
        ],
        provider=provider,
        model=model,
        validate=is_socratic_payload,
        schema_name="socratic",
        max_tokens=1000,
        temperature=0.5,
    )
