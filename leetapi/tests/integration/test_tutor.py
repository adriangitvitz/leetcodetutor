"""Integration tests for `POST /tutor/{slug}/explain`.

Covers the full LLM call lifecycle from the plan:
- Cold call → 1 LLM hit, response cached.
- Warm call → 0 LLM hits, served from DB.
- Switch persona → 1 LLM hit (different cache key); other personas untouched.
- Regenerate (force=true) → exactly 1 LLM hit; other personas' rows untouched.
- 5 concurrent same-key requests → dedup → exactly 1 LLM hit.
- 4 concurrent different-persona requests → 4 separate LLM hits.
- LLM JSON failure → one stricter retry.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx

LEETCODE_URL = "https://leetcode.com/graphql/"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LEETCODE_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "leetcode_two_sum.json"

# A valid teacher payload matching `is_teacher_payload`.
TEACHER_PAYLOAD = {
    "plain": "Find two indices in `nums` whose values sum to `target`.",
    "aha": "Naive O(n^2) is wasted work — a hash map turns 'have I seen complement?' into O(1).",
    "strategy": "1. Walk left to right.\n2. For each x, look up `target - x` in a dict.\n3. Hit → return both indices. Miss → store x's index.",
    "code": "<pre><span class=\"kw\">def</span> two_sum(nums, target):\n    seen = {}\n    <span class=\"kw\">for</span> i, x <span class=\"kw\">in</span> enumerate(nums):\n        need = target - x\n        <span class=\"kw\">if</span> need <span class=\"kw\">in</span> seen: <span class=\"kw\">return</span> [seen[need], i]\n        seen[x] = i</pre>",
    "complexity": {
        "time": "O(n)",
        "space": "O(n)",
        "tdesc": "Single pass over the array.",
        "sdesc": "Hash map holds up to n entries.",
    },
}


def _openai_response(payload: dict) -> dict:
    """Wrap a JSON payload in an OpenAI chat-completions response shape."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(payload)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _leetcode_response() -> dict:
    return json.loads(LEETCODE_FIXTURE.read_text())


@pytest.fixture
def mock_apis():
    """Mocks both LeetCode GraphQL and OpenRouter chat completions."""
    with respx.mock(assert_all_called=False) as mock:
        mock.post(LEETCODE_URL).mock(
            return_value=httpx.Response(200, json=_leetcode_response())
        )
        mock.post(OPENROUTER_URL).mock(
            return_value=httpx.Response(200, json=_openai_response(TEACHER_PAYLOAD))
        )
        yield mock


def _scholar_body(force: bool = False) -> dict:
    return {
        "kind": "teacher",
        "provider": "openrouter",
        "model": "anthropic/claude-sonnet-4.5",
        "persona": "scholar",
        "force": force,
    }


# ---------- cold + warm -------------------------------------------------


async def test_cold_call_invokes_llm_once_and_caches(loaded_catalog, mock_apis):
    r = await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
    assert r.status_code == 200
    body = r.json()
    assert body["cached"] is False
    assert body["payload"]["plain"].startswith("Find two indices")
    # Exactly one LLM call.
    openrouter_calls = [c for c in mock_apis.calls if "openrouter" in str(c.request.url)]
    assert len(openrouter_calls) == 1


async def test_warm_call_serves_from_cache_no_llm(loaded_catalog, mock_apis):
    await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
    pre_count = len([c for c in mock_apis.calls if "openrouter" in str(c.request.url)])

    for _ in range(3):
        r = await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
        assert r.status_code == 200
        assert r.json()["cached"] is True

    post_count = len([c for c in mock_apis.calls if "openrouter" in str(c.request.url)])
    assert pre_count == post_count == 1  # no new LLM calls


# ---------- per-persona partitioning ------------------------------------


async def test_switching_persona_creates_a_new_row_others_preserved(loaded_catalog, mock_apis):
    # Generate Scholar.
    await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
    # Generate Coach (different persona → different cache key → new LLM call).
    coach_body = {**_scholar_body(), "persona": "coach"}
    await loaded_catalog.post("/tutor/two-sum/explain", json=coach_body)

    # Each persona generated once.
    openrouter_calls = [c for c in mock_apis.calls if "openrouter" in str(c.request.url)]
    assert len(openrouter_calls) == 2

    # Switching back to Scholar must hit the cache, not regenerate.
    r = await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
    assert r.json()["cached"] is True

    openrouter_calls = [c for c in mock_apis.calls if "openrouter" in str(c.request.url)]
    assert len(openrouter_calls) == 2  # unchanged


async def test_regenerate_is_scoped_to_active_persona(loaded_catalog, mock_apis):
    """force=true on Scholar must NOT touch Coach's cached row."""
    await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body())
    coach_body = {**_scholar_body(), "persona": "coach"}
    await loaded_catalog.post("/tutor/two-sum/explain", json=coach_body)

    pre = len([c for c in mock_apis.calls if "openrouter" in str(c.request.url)])
    assert pre == 2

    # Regenerate Scholar.
    r = await loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body(force=True))
    assert r.json()["cached"] is False

    # +1 LLM call (Scholar regen). Coach still cached.
    post = len([c for c in mock_apis.calls if "openrouter" in str(c.request.url)])
    assert post == 3

    r2 = await loaded_catalog.post("/tutor/two-sum/explain", json=coach_body)
    assert r2.json()["cached"] is True
    final = len([c for c in mock_apis.calls if "openrouter" in str(c.request.url)])
    assert final == 3


# ---------- dedup of concurrent requests --------------------------------


async def test_concurrent_same_key_dedup_to_one_llm_call(loaded_catalog, mock_apis):
    results = await asyncio.gather(
        *(loaded_catalog.post("/tutor/two-sum/explain", json=_scholar_body()) for _ in range(5))
    )
    assert all(r.status_code == 200 for r in results)
    openrouter_calls = [c for c in mock_apis.calls if "openrouter" in str(c.request.url)]
    assert len(openrouter_calls) == 1, "5 parallel same-key requests must dedup to 1 LLM call"


async def test_concurrent_different_personas_no_dedup(loaded_catalog, mock_apis):
    """4 parallel requests for 4 different personas → 4 LLM calls (different keys)."""
    results = await asyncio.gather(
        *(
            loaded_catalog.post(
                "/tutor/two-sum/explain",
                json={**_scholar_body(), "persona": p},
            )
            for p in ("scholar", "coach", "sage", "hacker")
        )
    )
    assert all(r.status_code == 200 for r in results)
    openrouter_calls = [c for c in mock_apis.calls if "openrouter" in str(c.request.url)]
    assert len(openrouter_calls) == 4


# ---------- bad inputs --------------------------------------------------


async def test_unknown_persona_returns_400(loaded_catalog):
    body = {**_scholar_body(), "persona": "wizard"}
    r = await loaded_catalog.post("/tutor/two-sum/explain", json=body)
    assert r.status_code == 400


async def test_unknown_kind_returns_400(loaded_catalog):
    body = {**_scholar_body(), "kind": "philosophical"}
    r = await loaded_catalog.post("/tutor/two-sum/explain", json=body)
    assert r.status_code == 400


async def test_unknown_slug_returns_404(loaded_catalog):
    r = await loaded_catalog.post("/tutor/never-asked/explain", json=_scholar_body())
    assert r.status_code == 404


# ---------- JSON failure → stricter retry recovers ----------------------


async def test_malformed_json_first_then_good_recovers():
    """First LLM response is non-JSON; the wrapper should retry once with a
    stricter prompt and succeed on the second try."""
    from leetapi.services.llm import complete_json_with_retry
    from leetapi.services.tutor import is_teacher_payload

    bad_response = httpx.Response(
        200,
        json=_openai_response({}),  # empty dict — fails validate
    )
    good_response = httpx.Response(200, json=_openai_response(TEACHER_PAYLOAD))

    with respx.mock() as mock:
        route = mock.post(OPENROUTER_URL)
        # First call returns bad shape; second returns good.
        route.side_effect = [bad_response, good_response]

        data = await complete_json_with_retry(
            [{"role": "user", "content": "noop"}],
            provider="openrouter",
            model="anthropic/claude-sonnet-4.5",
            validate=is_teacher_payload,
            schema_name="teacher",
        )
        assert data["plain"].startswith("Find two indices")
        assert route.call_count == 2
