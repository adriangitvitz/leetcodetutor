from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..models import Problem, ProblemCompany
from .topics import TOPIC_GROUPS, top_topic_from_weighted_tags

@dataclass
class Ask:
    slug: str
    title: str
    difficulty: str
    topics: str
    link: str
    frequency: float


async def asks_for_company(session: AsyncSession, company: str) -> list[Ask]:
    stmt = (
        select(
            Problem.slug,
            Problem.title,
            Problem.difficulty,
            Problem.topics,
            Problem.link,
            ProblemCompany.frequency,
        )
        .join(ProblemCompany, ProblemCompany.slug == Problem.slug)
        .where(ProblemCompany.company == company)
        .order_by(desc(ProblemCompany.frequency))
    )
    rows = (await session.execute(stmt)).all()
    return [Ask(slug=r[0], title=r[1], difficulty=r[2], topics=r[3], link=r[4], frequency=r[5]) for r in rows]


async def top_topic_for_company(
    session: AsyncSession, company: str
) -> tuple[str | None, float]:
    asks = await asks_for_company(session, company)
    return top_topic_from_weighted_tags((a.topics, a.frequency) for a in asks)


async def signature_problem_for_company(
    session: AsyncSession, company: str
) -> Ask | None:
    asks = await asks_for_company(session, company)
    return asks[0] if asks else None


async def related_problems_for_company(
    session: AsyncSession,
    company: str,
    *,
    limit: int = 8,
) -> list[Ask]:
    top_topic, _ = await top_topic_for_company(session, company)
    if top_topic is None:
        return []
    members = TOPIC_GROUPS.get(top_topic, [])
    if not members:
        return []

    asked_slugs_stmt = select(ProblemCompany.slug).where(ProblemCompany.company == company)
    asked = set((await session.scalars(asked_slugs_stmt)).all())

    where_clauses = []
    for tag in members:
        where_clauses.append(Problem.topics.like(f"%{tag}%"))
    from sqlalchemy import or_

    stmt = (
        select(
            Problem.slug,
            Problem.title,
            Problem.difficulty,
            Problem.topics,
            Problem.link,
            Problem.mean_frequency,
        )
        .where(or_(*where_clauses))
        .order_by(desc(Problem.company_count), desc(Problem.mean_frequency))
        .limit(limit + len(asked))  # over-fetch to compensate for filtered ones
    )
    rows = (await session.execute(stmt)).all()
    out: list[Ask] = []
    for r in rows:
        if r[0] in asked:
            continue
        out.append(Ask(slug=r[0], title=r[1], difficulty=r[2], topics=r[3], link=r[4], frequency=r[5]))
        if len(out) >= limit:
            break
    return out


@dataclass
class TopProblem:
    slug: str
    title: str
    difficulty: str
    topics: str
    link: str
    company_count: int
    mean_frequency: float
    score: float  # company_count × mean_frequency — single ranking metric


@dataclass
class TopTopic:
    name: str
    score: float


@dataclass
class GlobalStats:
    top_problems: list[TopProblem]
    top_topics: list[TopTopic]
    difficulty_mix: dict[str, float]  # weighted by mean_frequency × company_count


async def global_stats(
    session: AsyncSession,
    *,
    top_problems_limit: int = 30,
) -> GlobalStats:
    score_col = (Problem.company_count * Problem.mean_frequency).label("score")
    stmt = (
        select(
            Problem.slug,
            Problem.title,
            Problem.difficulty,
            Problem.topics,
            Problem.link,
            Problem.company_count,
            Problem.mean_frequency,
            score_col,
        )
        .order_by(desc(score_col))
        .limit(top_problems_limit)
    )
    top_rows = (await session.execute(stmt)).all()
    top_problems = [
        TopProblem(
            slug=r[0], title=r[1], difficulty=r[2], topics=r[3], link=r[4],
            company_count=r[5], mean_frequency=r[6], score=float(r[7]),
        )
        for r in top_rows
    ]

    all_stmt = select(
        Problem.topics,
        Problem.difficulty,
        Problem.company_count,
        Problem.mean_frequency,
    )
    all_rows = (await session.execute(all_stmt)).all()

    weighted = ((topics, count * freq) for topics, _, count, freq in all_rows)
    tally: dict[str, float] = {}
    from .topics import groups_for_tags, split_tags

    diff_mix: dict[str, float] = {"EASY": 0.0, "MEDIUM": 0.0, "HARD": 0.0}
    for topics, difficulty, count, freq in all_rows:
        score = float(count) * float(freq)
        diff_mix[difficulty] = diff_mix.get(difficulty, 0.0) + score
        groups = groups_for_tags(split_tags(topics))
        if not groups:
            continue
        share = score / len(groups)
        for group in groups:
            tally[group] = tally.get(group, 0.0) + share

    order = {name: i for i, name in enumerate(TOPIC_GROUPS)}
    top_topics = sorted(
        (TopTopic(name=k, score=v) for k, v in tally.items()),
        key=lambda t: (-t.score, order.get(t.name, 1_000_000)),
    )

    return GlobalStats(
        top_problems=top_problems,
        top_topics=top_topics,
        difficulty_mix=diff_mix,
    )
