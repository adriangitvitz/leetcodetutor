"""Smoke tests for the small meta routes: `/models` and `/cache`."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

LEETCODE_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "leetcode_two_sum.json"


# ---------- /models ------------------------------------------------------


@pytest.fixture
def mock_openrouter_models():
    payload = {
        "data": [
            {"id": "anthropic/claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "context_length": 200000},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "context_length": 128000},
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get(OPENROUTER_MODELS_URL).mock(return_value=httpx.Response(200, json=payload))
        yield mock


async def test_models_openrouter_returns_sorted_list(client, mock_openrouter_models):
    r = await client.get("/models?provider=openrouter")
    assert r.status_code == 200
    body = r.json()
    assert body["error"] is None
    ids = [m["id"] for m in body["models"]]
    assert ids == sorted(ids)
    assert "anthropic/claude-sonnet-4.5" in ids


async def test_models_lmstudio_unreachable_returns_soft_error(client):
    """No mock for the LM Studio URL → soft error, empty list."""
    r = await client.get("/models?provider=lmstudio")
    assert r.status_code == 200
    body = r.json()
    assert body["models"] == []
    assert body["error"] is not None


async def test_models_unknown_provider(client):
    r = await client.get("/models?provider=mystery")
    assert r.status_code == 200
    body = r.json()
    assert body["models"] == []
    assert "unknown provider" in body["error"]


# ---------- /cache -------------------------------------------------------


async def test_cache_dump_empty(client):
    r = await client.get("/cache")
    assert r.status_code == 200
    assert r.json() == {"count": 0, "rows": []}


async def test_cache_dump_after_explain(loaded_catalog):
    """Generate one tutor response, then verify /cache surfaces it."""
    payload = {
        "plain": "p", "aha": "a", "strategy": "s", "code": "<pre>c</pre>",
        "complexity": {"time": "O(n)", "space": "O(1)", "tdesc": ".", "sdesc": "."},
    }
    openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
    with respx.mock(assert_all_called=False) as mock:
        mock.post("https://leetcode.com/graphql/").mock(
            return_value=httpx.Response(200, json=json.loads(LEETCODE_FIXTURE.read_text()))
        )
        mock.post(openrouter_url).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "x", "object": "chat.completion", "created": 0, "model": "x",
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(payload)}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
        )

        await loaded_catalog.post(
            "/tutor/two-sum/explain",
            json={
                "kind": "teacher",
                "provider": "openrouter",
                "model": "anthropic/claude-sonnet-4.5",
                "persona": "scholar",
            },
        )

    r = await loaded_catalog.get("/cache")
    body = r.json()
    assert body["count"] == 1
    row = body["rows"][0]
    assert row["slug"] == "two-sum"
    assert row["persona"] == "scholar"
    assert row["kind"] == "teacher"
    assert row["bytes"] > 0
