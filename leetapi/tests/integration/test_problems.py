"""Integration tests for `/problems` (rich filter), `/problems/{slug}`,
and `/companies`.

The `loaded_catalog` fixture pre-populates the in-memory DB with:
  - Two Sum         (EASY,   topics "Array, Hash Table",        companies: A, B, C)
  - LRU Cache       (MEDIUM, topics "Hash Table, Linked …",     companies: A)
  - N-Queens        (HARD,   topics "Array, Backtracking",      companies: B)
"""

from __future__ import annotations


# ---------- list endpoint: shape ----------------------------------------


async def test_list_returns_total_and_items(loaded_catalog):
    r = await loaded_catalog.get("/problems")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


async def test_list_default_sort_company_count_desc(loaded_catalog):
    r = await loaded_catalog.get("/problems")
    titles = [p["title"] for p in r.json()["items"]]
    # Two Sum has 3 companies; the others have 1 each.
    assert titles[0] == "Two Sum"


async def test_list_includes_companies_array(loaded_catalog):
    r = await loaded_catalog.get("/problems")
    by_slug = {p["slug"]: p for p in r.json()["items"]}
    assert sorted(by_slug["two-sum"]["companies"]) == ["CompanyA", "CompanyB", "CompanyC"]
    assert by_slug["lru-cache"]["companies"] == ["CompanyA"]


# ---------- filter: difficulty ------------------------------------------


async def test_filter_by_difficulty_single(loaded_catalog):
    r = await loaded_catalog.get("/problems?difficulty=MEDIUM")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "LRU Cache"


async def test_filter_by_difficulty_multi(loaded_catalog):
    r = await loaded_catalog.get("/problems?difficulty=EASY,HARD")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum", "N-Queens"}


# ---------- filter: topics ----------------------------------------------


async def test_filter_by_topics_any_substring(loaded_catalog):
    """`topics=array` matches any problem whose topics column contains 'array'."""
    r = await loaded_catalog.get("/problems?topics=array")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum", "N-Queens"}


async def test_filter_by_topics_all_must_contain_each(loaded_catalog):
    """`topics_all=array,backtracking` must match all listed topics."""
    r = await loaded_catalog.get("/problems?topics_all=array,backtracking")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"N-Queens"}


# ---------- filter: company JOIN ----------------------------------------


async def test_filter_by_single_company(loaded_catalog):
    r = await loaded_catalog.get("/problems?company=CompanyA")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum", "LRU Cache"}


async def test_filter_by_companies_all_intersection(loaded_catalog):
    """`companies_all=A,B` returns problems asked by *both* — only Two Sum."""
    r = await loaded_catalog.get("/problems?companies_all=CompanyA,CompanyB")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum"}


# ---------- filter: numeric thresholds ----------------------------------


async def test_filter_min_company_count(loaded_catalog):
    r = await loaded_catalog.get("/problems?min_company_count=2")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum"}


async def test_filter_min_frequency(loaded_catalog):
    """Two Sum mean_freq=90, LRU=75, N-Queens=60. Threshold 70 → drops N-Queens."""
    r = await loaded_catalog.get("/problems?min_frequency=70")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum", "LRU Cache"}


# ---------- filter: substring on title ----------------------------------


async def test_filter_title_contains(loaded_catalog):
    r = await loaded_catalog.get("/problems?title_contains=cache")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"LRU Cache"}


# ---------- filter: explicit slug list ----------------------------------


async def test_filter_by_slug_list(loaded_catalog):
    r = await loaded_catalog.get("/problems?slug=two-sum,n-queens")
    titles = {p["title"] for p in r.json()["items"]}
    assert titles == {"Two Sum", "N-Queens"}


# ---------- sort + paging -----------------------------------------------


async def test_sort_by_title_asc(loaded_catalog):
    r = await loaded_catalog.get("/problems?sort=title&order=asc")
    titles = [p["title"] for p in r.json()["items"]]
    assert titles == ["LRU Cache", "N-Queens", "Two Sum"]


async def test_limit_and_offset(loaded_catalog):
    r = await loaded_catalog.get("/problems?limit=1&offset=1&sort=title&order=asc")
    body = r.json()
    assert body["total"] == 3  # total ignores limit/offset
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "N-Queens"


# ---------- empty result ------------------------------------------------


async def test_empty_when_no_match(loaded_catalog):
    r = await loaded_catalog.get("/problems?difficulty=EASY&company=Nonexistent")
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------- single problem ----------------------------------------------


async def test_get_problem_by_slug(loaded_catalog):
    r = await loaded_catalog.get("/problems/lru-cache")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "LRU Cache"
    assert body["companies"] == ["CompanyA"]


async def test_get_problem_404_for_unknown_slug(loaded_catalog):
    r = await loaded_catalog.get("/problems/never-asked")
    assert r.status_code == 404


# ---------- /companies --------------------------------------------------


async def test_list_companies(loaded_catalog):
    r = await loaded_catalog.get("/companies")
    assert r.status_code == 200
    body = r.json()
    by_name = {c["name"]: c for c in body["items"]}
    assert set(by_name) == {"CompanyA", "CompanyB", "CompanyC"}
    # A and B each ask 2 problems (Two Sum + their second). C asks only Two Sum.
    assert by_name["CompanyA"]["problem_count"] == 2
    assert by_name["CompanyB"]["problem_count"] == 2
    assert by_name["CompanyC"]["problem_count"] == 1
