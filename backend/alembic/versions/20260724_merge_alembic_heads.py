"""merge Alembic heads before pre-production window

Revision ID: 20260724_merge_heads
Revises: 030, 20260716_class_snapshots
Create Date: 2026-07-24

This migration only reconciles the revision graph. It performs no DDL and
changes no application data.
"""

from collections.abc import Sequence


revision: str = "20260724_merge_heads"
down_revision: tuple[str, str] = ("030", "20260716_class_snapshots")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Merge the two existing branches without changing the schema."""


def downgrade() -> None:
    """Return the revision graph to the two previous heads."""
