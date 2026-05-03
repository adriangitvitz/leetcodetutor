"""Integration tests for the new By-Company and Statistics endpoints."""

from __future__ import annotations


# ---------- /companies (enrichment) -------------------------------------


async def test_companies_default_skips_topic_enrichment(loaded_catalog):
    r = await loaded_catalog.get("/companies")
    assert r.status_code == 200
    items = r.json()["items"]
    # No `with_topics` → top_topic stays null
    for c in items:
        assert c.get("top_topic") is None


async def test_companies_with_topics_includes_top_topic_and_signature(loaded_catalog):
    r = await loaded_catalog.get("/companies?with_topics=true")
    assert r.status_code == 200
    by_name = {c["name"]: c for c in r.json()["items"]}

    a = by_name["CompanyA"]
    assert a["top_topic"] is not None
    assert a["signature_title"] == "Two Sum"  # CompanyA's highest freq is Two Sum


# ---------- /companies/{name} -------------------------------------------


async def test_company_detail_has_asks_and_aggregates(loaded_catalog):
    r = await loaded_catalog.get("/companies/CompanyA")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "CompanyA"
    assert body["total_problems"] == 2
    assert body["top_topic"] is not None
    titles = [a["title"] for a in body["asks"]]
    assert titles == ["Two Sum", "LRU Cache"]  # sorted by frequency desc
    assert body["asks"][0]["frequency"] == 90.0


async def test_company_detail_404_for_unknown(loaded_catalog):
    r = await loaded_catalog.get("/companies/Nonexistent")
    assert r.status_code == 404


# ---------- /companies/{name}/related -----------------------------------


async def test_related_excludes_already_asked(loaded_catalog):
    r = await loaded_catalog.get("/companies/CompanyA/related?limit=20")
    assert r.status_code == 200
    slugs = {a["slug"] for a in r.json()}
    # CompanyA already asks two-sum and lru-cache
    assert "two-sum" not in slugs
    assert "lru-cache" not in slugs


async def test_related_404_for_unknown_company(loaded_catalog):
    r = await loaded_catalog.get("/companies/Nonexistent/related")
    assert r.status_code == 404


# ---------- /stats ------------------------------------------------------


async def test_stats_returns_top_problems(loaded_catalog):
    r = await loaded_catalog.get("/stats")
    assert r.status_code == 200
    body = r.json()
    titles = {p["title"] for p in body["top_problems"]}
    # Three fixture problems; all are "top" since N=3.
    assert {"Two Sum", "LRU Cache", "N-Queens"}.issubset(titles)


async def test_stats_top_problem_is_two_sum(loaded_catalog):
    r = await loaded_catalog.get("/stats")
    body = r.json()
    # Two Sum has 3 companies and high mean_frequency → top score.
    assert body["top_problems"][0]["title"] == "Two Sum"


async def test_stats_difficulty_mix_has_three_buckets(loaded_catalog):
    r = await loaded_catalog.get("/stats")
    mix = r.json()["difficulty_mix"]
    assert set(mix) == {"EASY", "MEDIUM", "HARD"}
    # All three difficulties present in the fixture.
    assert all(v > 0 for v in mix.values())


async def test_stats_top_topics_includes_arrays(loaded_catalog):
    r = await loaded_catalog.get("/stats")
    names = {t["name"] for t in r.json()["top_topics"]}
    assert "Arrays" in names
