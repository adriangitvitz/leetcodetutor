from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import Company, Problem, ProblemCompany

EXPECTED_COLS = {
    "Difficulty",
    "Title",
    "Frequency",
    "Acceptance Rate",
    "Link",
    "Topics",
}

@dataclass
class ProblemRow:
    slug: str
    link: str
    title: str
    difficulty: str
    acceptance_rate: float
    topics: str
    company_count: int
    mean_frequency: float
    max_frequency: float


@dataclass
class CompanyRow:
    name: str


@dataclass
class LinkRow:
    slug: str
    company: str
    frequency: float


@dataclass
class Aggregated:
    problems: list[ProblemRow] = field(default_factory=list)
    companies: list[CompanyRow] = field(default_factory=list)
    links: list[LinkRow] = field(default_factory=list)


def _slug_from_link(link: str) -> str:
    return link.rstrip("/").rsplit("/", 1)[-1]


def _load_company_frames(problems_dir: Path) -> list[pd.DataFrame]:
    frames: list[pd.DataFrame] = []
    for csv_path in sorted(problems_dir.glob("*/5. All.csv")):
        company = csv_path.parent.name
        try:
            df = pd.read_csv(csv_path)
        except pd.errors.EmptyDataError:
            continue
        if df.empty:
            continue
        missing = EXPECTED_COLS - set(df.columns)
        if missing:
            print(
                f"[importer] {company}: missing columns {missing}, skipping",
                file=sys.stderr,
            )
            continue
        df["Company"] = company
        frames.append(df)
    return frames


def aggregate(problems_dir: Path) -> Aggregated:
    frames = _load_company_frames(problems_dir)
    if not frames:
        return Aggregated()

    raw = pd.concat(frames, ignore_index=True)
    raw = raw.drop_duplicates(subset=["Link", "Company"])
    raw["slug"] = raw["Link"].map(_slug_from_link)
    for col in ("Title", "Difficulty", "Topics"):
        raw[col] = raw[col].fillna("")
    for col in ("Frequency", "Acceptance Rate"):
        raw[col] = raw[col].fillna(0.0)

    grouped = raw.groupby("Link", as_index=False).agg(
        title=("Title", "first"),
        difficulty=("Difficulty", "first"),
        acceptance_rate=("Acceptance Rate", "first"),
        topics=("Topics", "first"),
        company_count=("Company", "nunique"),
        mean_frequency=("Frequency", "mean"),
        max_frequency=("Frequency", "max"),
    )
    grouped["slug"] = grouped["Link"].map(_slug_from_link)
    grouped["mean_frequency"] = grouped["mean_frequency"].round(2)

    problem_rows = [
        ProblemRow(
            slug=row.slug,
            link=row.Link,
            title=row.title,
            difficulty=row.difficulty,
            acceptance_rate=float(row.acceptance_rate),
            topics=row.topics,
            company_count=int(row.company_count),
            mean_frequency=float(row.mean_frequency),
            max_frequency=float(row.max_frequency),
        )
        for row in grouped.itertuples(index=False)
    ]

    company_names = sorted({str(c) for c in raw["Company"].unique()})
    company_rows = [CompanyRow(name=name) for name in company_names]

    link_rows = [
        LinkRow(slug=row.slug, company=row.Company, frequency=float(row.Frequency))
        for row in raw.itertuples(index=False)
    ]

    return Aggregated(problems=problem_rows, companies=company_rows, links=link_rows)

def _insert_for(session: AsyncSession):
    bind = session.get_bind()
    name = bind.dialect.name
    if name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        return pg_insert
    if name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        return sqlite_insert
    raise NotImplementedError(f"upsert not implemented for dialect {name!r}")

_BATCH = 500

def _chunked(items: list, size: int = _BATCH):
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def _upsert_companies(session: AsyncSession, rows: list[CompanyRow]) -> None:
    if not rows:
        return
    insert = _insert_for(session)
    for batch in _chunked(rows):
        stmt = insert(Company).values([{"name": r.name} for r in batch])
        stmt = stmt.on_conflict_do_nothing(index_elements=["name"])
        await session.execute(stmt)


async def _upsert_problems(session: AsyncSession, rows: list[ProblemRow]) -> None:
    if not rows:
        return
    insert = _insert_for(session)
    update_cols = (
        "link",
        "title",
        "difficulty",
        "acceptance_rate",
        "topics",
        "company_count",
        "mean_frequency",
        "max_frequency",
    )
    for batch in _chunked(rows):
        payload = [
            {
                "slug": r.slug,
                "link": r.link,
                "title": r.title,
                "difficulty": r.difficulty,
                "acceptance_rate": r.acceptance_rate,
                "topics": r.topics,
                "company_count": r.company_count,
                "mean_frequency": r.mean_frequency,
                "max_frequency": r.max_frequency,
            }
            for r in batch
        ]
        stmt = insert(Problem).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug"],
            set_={col: getattr(stmt.excluded, col) for col in update_cols},
        )
        await session.execute(stmt)


async def _upsert_links(session: AsyncSession, rows: list[LinkRow]) -> None:
    if not rows:
        return
    insert = _insert_for(session)
    for batch in _chunked(rows):
        payload = [
            {"slug": r.slug, "company": r.company, "frequency": r.frequency}
            for r in batch
        ]
        stmt = insert(ProblemCompany).values(payload)
        stmt = stmt.on_conflict_do_update(
            index_elements=["slug", "company"],
            set_={"frequency": stmt.excluded.frequency},
        )
        await session.execute(stmt)


async def ingest_csvs(session: AsyncSession, problems_dir: Path) -> Aggregated:
    agg = aggregate(problems_dir)
    if not agg.problems:
        return agg

    await _upsert_companies(session, agg.companies)
    await _upsert_problems(session, agg.problems)
    await _upsert_links(session, agg.links)
    await session.commit()
    return agg


async def count_problems(session: AsyncSession) -> int:
    result = await session.exec(select(Problem))
    return len(result.all())
