from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException
from openai import AsyncOpenAI

from ..config import get_settings


@dataclass(frozen=True)
class _ProviderConfig:
    base_url: str
    api_key: str
    default_model: str
    extra_headers: dict[str, str] | None = None


def _provider_config(name: str) -> _ProviderConfig:
    s = get_settings()
    name = (name or s.llm_provider).lower()
    if name == "openrouter":
        if not s.openrouter_api_key:
            raise HTTPException(
                status_code=502,
                detail="OPENROUTER_API_KEY is not set in the environment",
            )
        return _ProviderConfig(
            base_url="https://openrouter.ai/api/v1",
            api_key=s.openrouter_api_key,
            default_model=s.openrouter_model,
            extra_headers={
                "HTTP-Referer": s.openrouter_referer,
                "X-Title": "leetapi",
            },
        )
    if name == "lmstudio":
        return _ProviderConfig(
            base_url=s.lmstudio_url,
            api_key="lm-studio",
            default_model=s.lmstudio_model,
        )
    if name == "mlx":
        return _ProviderConfig(
            base_url=s.mlx_url,
            api_key="mlx",
            default_model=s.mlx_model,
        )
    raise HTTPException(status_code=400, detail=f"unknown provider: {name!r}")


def _client(cfg: _ProviderConfig) -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        default_headers=cfg.extra_headers,
    )

async def complete(
    messages: list[dict],
    *,
    provider: str,
    model: str | None = None,
    max_tokens: int = 800,
    temperature: float = 0.7,
) -> str:
    cfg = _provider_config(provider)
    client = _client(cfg)
    completion = await client.chat.completions.create(
        model=model or cfg.default_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return (completion.choices[0].message.content or "") if completion.choices else ""


async def complete_json(
    messages: list[dict],
    *,
    provider: str,
    model: str | None = None,
    max_tokens: int = 1500,
    temperature: float = 0.4,
) -> dict:
    cfg = _provider_config(provider)
    client = _client(cfg)
    completion = await client.chat.completions.create(
        model=model or cfg.default_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    raw = (completion.choices[0].message.content or "") if completion.choices else ""
    parsed = _parse_json_loose(raw)
    if parsed is None:
        raise HTTPException(
            status_code=502,
            detail=f"model returned non-JSON content: {raw[:160]!r}",
        )
    return parsed


def _parse_json_loose(text: str) -> dict | None:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        out = json.loads(cleaned)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        # Try to extract the largest {...} substring.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                out = json.loads(cleaned[start : end + 1])
                return out if isinstance(out, dict) else None
            except json.JSONDecodeError:
                return None
        return None


async def complete_json_with_retry(
    messages: list[dict],
    *,
    provider: str,
    model: str | None,
    validate: Callable[[dict], bool],
    schema_name: str,
    max_tokens: int = 1500,
    temperature: float = 0.4,
) -> dict:
    first_error: str | None = None
    try:
        data = await complete_json(
            messages,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if validate(data):
            return data
        first_error = f"first pass: shape mismatch for {schema_name}"
    except HTTPException as exc:
        first_error = str(exc.detail)

    stricter = list(messages) + [
        {
            "role": "system",
            "content": (
                f"Your previous reply could not be parsed as a JSON object matching "
                f"the {schema_name} schema (reason: {first_error}). Reply ONLY with "
                "the JSON object — no prose, no markdown fences, no commentary. "
                "Do not repeat the schema in your output."
            ),
        }
    ]
    data = await complete_json(
        stricter,
        provider=provider,
        model=model,
        max_tokens=max_tokens,
        temperature=0.2,
    )
    if not validate(data):
        raise HTTPException(
            status_code=502,
            detail=f"retry also failed: {schema_name} schema mismatch (model: {model})",
        )
    return data
