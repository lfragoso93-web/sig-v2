"""widen asset universe membership source

Revision ID: 20260811_asset_univ_source64
Revises: 20260811_asset_universe_map
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_asset_univ_source64"
down_revision: str = "20260811_asset_universe_map"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "asset_universe_memberships",
        "source",
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "asset_universe_memberships",
        "source",
        existing_type=sa.String(length=64),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
