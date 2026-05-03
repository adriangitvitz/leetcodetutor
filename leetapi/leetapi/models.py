from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Problem(SQLModel, table=True):
    __tablename__ = "problems"

    slug: str = Field(primary_key=True)
    link: str = Field(unique=True)
    title: str = Field(index=True)
    difficulty: str = Field(index=True)
    acceptance_rate: float
    topics: str = Field(index=True)
    company_count: int = Field(index=True)
    mean_frequency: float
    max_frequency: float


class Company(SQLModel, table=True):
    __tablename__ = "companies"

    name: str = Field(primary_key=True)


class ProblemCompany(SQLModel, table=True):
    __tablename__ = "problem_companies"

    slug: str = Field(
        primary_key=True,
        foreign_key="problems.slug",
        ondelete="CASCADE",
        index=True,
    )
    company: str = Field(
        primary_key=True,
        foreign_key="companies.name",
        ondelete="CASCADE",
        index=True,
    )
    frequency: float


class Statement(SQLModel, table=True):
    __tablename__ = "statements"

    slug: str = Field(
        primary_key=True,
        foreign_key="problems.slug",
        ondelete="CASCADE",
    )
    content: str
    fetched_at: datetime = Field(default_factory=_utcnow)


class TutorResponse(SQLModel, table=True):
    __tablename__ = "tutor_responses"

    slug: str = Field(
        primary_key=True,
        foreign_key="problems.slug",
        ondelete="CASCADE",
    )
    provider: str = Field(primary_key=True)
    model: str = Field(primary_key=True)
    persona: str = Field(primary_key=True)
    kind: str = Field(primary_key=True)
    payload: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=_utcnow)
    refreshed_at: datetime = Field(default_factory=_utcnow)
    request_id: str | None = None
