"""create asset aliases

Revision ID: 20260712_asset_aliases
Revises: 029
"""
from alembic import op
import sqlalchemy as sa

revision = "20260712_asset_aliases"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("alias_ticker", sa.String(), nullable=False),
        sa.Column("asset_type", sa.String(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_provider", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("alias_ticker", "asset_type", name="uq_asset_aliases_ticker_type"),
    )
    op.create_index("ix_asset_aliases_asset_id", "asset_aliases", ["asset_id"])
    op.create_index("ix_asset_aliases_alias_ticker", "asset_aliases", ["alias_ticker"])


def downgrade() -> None:
    op.drop_index("ix_asset_aliases_alias_ticker", table_name="asset_aliases")
    op.drop_index("ix_asset_aliases_asset_id", table_name="asset_aliases")
    op.drop_table("asset_aliases")
