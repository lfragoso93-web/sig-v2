"""merge current runtime migration heads

Revision ID: 20260911_merge_runtime
Revises: 20260906_rate_source32, 20260910_goals_runtime
Create Date: 2026-09-11

This migration only reconciles the Alembic revision graph. It performs no DDL
and changes no application data.
"""

from collections.abc import Sequence


revision: str = "20260911_merge_runtime"
down_revision: tuple[str, str] = (
    "20260906_rate_source32",
    "20260910_goals_runtime",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the current runtime branches without changing the schema."""


def downgrade() -> None:
    """Return the revision graph to the two previous heads."""
