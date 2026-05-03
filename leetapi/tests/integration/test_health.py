"""Smoke test — proves the FastAPI app boots, the in-memory DB engine wires
up cleanly, and the test client roundtrips one request."""

from __future__ import annotations


async def test_health(client) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
