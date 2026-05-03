from __future__ import annotations

from pydantic import BaseModel


class ProblemSummary(BaseModel):
    slug: str
    title: str
    difficulty: str
    topics: str
    company_count: int
    mean_frequency: float
    max_frequency: float
    acceptance_rate: float
    link: str
    companies: list[str] = []


class ProblemList(BaseModel):
    total: int
    items: list[ProblemSummary]


class CompanyEntry(BaseModel):
    name: str
    problem_count: int
    top_topic: str | None = None
    top_topic_score: float | None = None
    signature_slug: str | None = None
    signature_title: str | None = None


class CompanyList(BaseModel):
    total: int
    items: list[CompanyEntry]


class AskEntry(BaseModel):
    slug: str
    title: str
    difficulty: str
    topics: str
    link: str
    frequency: float


class CompanyDetail(BaseModel):
    name: str
    total_problems: int
    top_topic: str | None
    top_topic_score: float
    avg_frequency: float
    asks: list[AskEntry]


class TopProblemEntry(BaseModel):
    slug: str
    title: str
    difficulty: str
    topics: str
    link: str
    company_count: int
    mean_frequency: float
    score: float


class TopTopicEntry(BaseModel):
    name: str
    score: float


class StatsResponse(BaseModel):
    top_problems: list[TopProblemEntry]
    top_topics: list[TopTopicEntry]
    difficulty_mix: dict[str, float]


class ExplainRequest(BaseModel):
    kind: str
    provider: str
    model: str
    persona: str
    force: bool = False


class ExplainResponse(BaseModel):
    payload: dict
    cached: bool
    request_id: str


class CompleteMessage(BaseModel):
    role: str
    content: str


class CompleteRequest(BaseModel):
    messages: list[CompleteMessage]
    provider: str | None = None
    model: str | None = None
    max_tokens: int = 800
    temperature: float = 0.7


class CompleteResponse(BaseModel):
    text: str
    provider: str
    model: str
    request_id: str

class CacheRow(BaseModel):
    slug: str
    provider: str
    model: str
    persona: str
    kind: str
    bytes: int
    created_at: str
    refreshed_at: str


class CacheDump(BaseModel):
    count: int
    rows: list[CacheRow]


class ModelEntry(BaseModel):
    id: str
    name: str
    context_length: int | None = None


class ModelList(BaseModel):
    models: list[ModelEntry]
    error: str | None = None
