"""add typed Treasury instrument metadata

Revision ID: 20261008_treasury_instruments
Revises: 20261005_real_data_cert
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261008_treasury_instruments"
down_revision: str = "20261005_real_data_cert"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "treasury_instruments",
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("commercial_name", sa.String(length=255), nullable=True),
        sa.Column("bond_type", sa.String(length=64), nullable=True),
        sa.Column("indexer", sa.String(length=64), nullable=True),
        sa.Column("coupon_type", sa.String(length=64), nullable=True),
        sa.Column("maturity_date", sa.Date(), nullable=True),
        sa.Column("official_code", sa.String(length=100), nullable=True),
        sa.Column("issuer", sa.String(length=100), nullable=True),
        sa.Column("trading_status", sa.String(length=32), nullable=True),
        sa.Column("metadata_source", sa.String(length=64), nullable=True),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "source_observed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_treasury_instruments_asset",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "asset_id",
            name="pk_treasury_instruments",
        ),
    )


def downgrade() -> None:
    op.drop_table("treasury_instruments")
