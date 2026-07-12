"""
create_asset_aliases

Revision ID: 028
Revises: 027
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("alias_ticker", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_provider", sa.String(), nullable=False, server_default="market_data_provider"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias_ticker", "asset_type", name="uq_asset_aliases_ticker_type"),
    )
    op.create_index("ix_asset_aliases_id", "asset_aliases", ["id"], unique=False)
    op.create_index("ix_asset_aliases_asset_id", "asset_aliases", ["asset_id"], unique=False)
    op.create_index("ix_asset_aliases_alias_ticker", "asset_aliases", ["alias_ticker"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_asset_aliases_alias_ticker", table_name="asset_aliases")
    op.drop_index("ix_asset_aliases_asset_id", table_name="asset_aliases")
    op.drop_index("ix_asset_aliases_id", table_name="asset_aliases")
    op.drop_table("asset_aliases")
