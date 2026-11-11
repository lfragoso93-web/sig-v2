"""add portfolio_corporate_fraction_settlements table

Revision ID: 20261111_fraction_settlements
Revises: 20261105_purge_cert_entities
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_fraction_settlements"
down_revision: str | None = "20261105_purge_cert_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portfolio_corporate_fraction_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.Integer(),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_event_id", sa.String(length=160), nullable=False),
        sa.Column("ticker", sa.String(length=30), nullable=False),
        sa.Column("gross_amount_brl", sa.Numeric(18, 2), nullable=False),
        sa.Column("settlement_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "gross_amount_brl >= 0",
            name="ck_portfolio_corp_fraction_settlement_nonneg",
        ),
        sa.UniqueConstraint(
            "portfolio_id",
            "source_event_id",
            name="uq_portfolio_corp_fraction_settlement",
        ),
    )
    op.create_index(
        "ix_portfolio_corp_fraction_settlements_portfolio_id",
        "portfolio_corporate_fraction_settlements",
        ["portfolio_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_portfolio_corp_fraction_settlements_portfolio_id",
        table_name="portfolio_corporate_fraction_settlements",
    )
    op.drop_table("portfolio_corporate_fraction_settlements")
