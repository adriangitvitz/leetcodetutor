"""Initial schema: problems, companies, problem_companies, statements, tutor_responses.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-02

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("link", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("acceptance_rate", sa.Float(), nullable=False),
        sa.Column("topics", sa.String(), nullable=False),
        sa.Column("company_count", sa.Integer(), nullable=False),
        sa.Column("mean_frequency", sa.Float(), nullable=False),
        sa.Column("max_frequency", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
        sa.UniqueConstraint("link"),
    )
    op.create_index("ix_problems_title", "problems", ["title"])
    op.create_index("ix_problems_difficulty", "problems", ["difficulty"])
    op.create_index("ix_problems_topics", "problems", ["topics"])
    op.create_index("ix_problems_company_count", "problems", ["company_count"])
    # Composite index supporting the default sort `ORDER BY company_count DESC,
    # mean_frequency DESC LIMIT N`.
    op.create_index(
        "ix_problems_rank",
        "problems",
        [sa.text("company_count DESC"), sa.text("mean_frequency DESC")],
    )

    op.create_table(
        "companies",
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )

    op.create_table(
        "problem_companies",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("frequency", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["slug"], ["problems.slug"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company"], ["companies.name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slug", "company"),
    )
    op.create_index("ix_problem_companies_slug", "problem_companies", ["slug"])
    op.create_index("ix_problem_companies_company", "problem_companies", ["company"])

    op.create_table(
        "statements",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["slug"], ["problems.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slug"),
    )

    op.create_table(
        "tutor_responses",
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("persona", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["slug"], ["problems.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slug", "provider", "model", "persona", "kind"),
    )


def downgrade() -> None:
    op.drop_table("tutor_responses")
    op.drop_table("statements")
    op.drop_index("ix_problem_companies_company", table_name="problem_companies")
    op.drop_index("ix_problem_companies_slug", table_name="problem_companies")
    op.drop_table("problem_companies")
    op.drop_table("companies")
    op.drop_index("ix_problems_rank", table_name="problems")
    op.drop_index("ix_problems_company_count", table_name="problems")
    op.drop_index("ix_problems_topics", table_name="problems")
    op.drop_index("ix_problems_difficulty", table_name="problems")
    op.drop_index("ix_problems_title", table_name="problems")
    op.drop_table("problems")
