"""add official market calendar facts

Revision ID: 20261009_market_calendar
Revises: 20261008_treasury_instruments
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_market_calendar"
down_revision: str = "20261008_treasury_instruments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_calendar_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("calendar_date", sa.Date(), nullable=False),
        sa.Column("is_business_day", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=512), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("market", "calendar_date", name="uq_market_calendar_day"),
    )
    op.create_index("ix_market_calendar_days_market_date", "market_calendar_days", ["market", "calendar_date"])


def downgrade() -> None:
    op.drop_index("ix_market_calendar_days_market_date", table_name="market_calendar_days")
    op.drop_table("market_calendar_days")
