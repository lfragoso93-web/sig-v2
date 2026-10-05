"""add proven rate history coverage intervals

Revision ID: 20260906_rate_coverage
Revises: 20260903_drop_fixed_income
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_rate_coverage"
down_revision: str = "20260903_drop_fixed_income"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_history_coverages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("indicator", sa.String(length=10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_date >= start_date",
            name="ck_rate_history_coverages_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "indicator",
            "start_date",
            "end_date",
            "source",
            name="uq_rate_history_coverages_identity",
        ),
    )
    op.create_index(
        "ix_rate_history_coverages_indicator_range",
        "rate_history_coverages",
        ["indicator", "start_date", "end_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rate_history_coverages_indicator_range",
        table_name="rate_history_coverages",
    )
    op.drop_table("rate_history_coverages")
