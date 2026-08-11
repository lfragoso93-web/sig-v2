"""add persisted asset universe memberships

Revision ID: 20260811_asset_universe_memberships
Revises: 20260807_pos_snap_ts_nn
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_asset_universe_memberships"
down_revision: str = "20260807_pos_snap_ts_nn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset_universe_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("universe_key", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id",
            "universe_key",
            name="uq_asset_universe_membership_asset_universe",
        ),
    )
    op.create_index(
        "ix_asset_universe_memberships_asset_id",
        "asset_universe_memberships",
        ["asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_asset_universe_memberships_universe_rank",
        "asset_universe_memberships",
        ["universe_key", "rank"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_asset_universe_memberships_universe_rank",
        table_name="asset_universe_memberships",
    )
    op.drop_index(
        "ix_asset_universe_memberships_asset_id",
        table_name="asset_universe_memberships",
    )
    op.drop_table("asset_universe_memberships")
