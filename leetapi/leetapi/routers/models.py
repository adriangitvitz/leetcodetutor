from __future__ import annotations

import httpx
from fastapi import APIRouter, Query

from ..config import get_settings
from ..schemas import ModelEntry, ModelList

router = APIRouter(prefix="/models", tags=["meta"])


@router.get("", response_model=ModelList)
async def list_models(
    provider: str = Query("openrouter", description="openrouter | lmstudio | mlx"),
) -> ModelList:
    if provider == "openrouter":
        return await _openrouter()
    if provider in ("lmstudio", "mlx"):
        return await _local_provider(provider)
    return ModelList(models=[], error=f"unknown provider: {provider!r}")


async def _openrouter() -> ModelList:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            payload = r.json()
    except Exception as exc:  # noqa: BLE001
        return ModelList(models=[], error=f"OpenRouter fetch failed: {exc}")

    items = []
    for m in payload.get("data", []):
        if not isinstance(m.get("id"), str):
            continue
        items.append(
            ModelEntry(
                id=m["id"],
                name=m.get("name") or m["id"],
                context_length=m.get("context_length"),
            )
        )
    items.sort(key=lambda x: x.id)
    return ModelList(models=items)


async def _local_provider(provider: str) -> ModelList:
    s = get_settings()
    base = (s.lmstudio_url if provider == "lmstudio" else s.mlx_url).rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/models", headers={"Accept": "application/json"})
            r.raise_for_status()
            payload = r.json()
    except Exception as exc:  # noqa: BLE001
        return ModelList(models=[], error=f"{provider} unreachable: {exc}")

    items = [
        ModelEntry(id=m["id"], name=m["id"])
        for m in payload.get("data", [])
        if isinstance(m.get("id"), str)
    ]
    return ModelList(models=items)
