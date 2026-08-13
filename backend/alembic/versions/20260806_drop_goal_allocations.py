"""contract unused goal allocations table

Revision ID: 20260806_drop_goal_allocations
Revises: 20260731_corp_event_catalog
Create Date: 2026-08-06

The current goals runtime has no consumer for ``goal_allocations``. This
contraction is guarded: the migration refuses to remove the table when any row
exists, so no business data can be discarded silently.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_drop_goal_allocations"
down_revision: str = "20260731_corp_event_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _assert_empty(bind: sa.engine.Connection) -> None:
    inspector = sa.inspect(bind)
    if not inspector.has_table("goal_allocations"):
        return

    row_count = int(
        bind.execute(sa.text("SELECT COUNT(*) FROM goal_allocations")).scalar_one()
    )
    if row_count:
        raise RuntimeError(
            "physical contraction blocked: goal_allocations contains "
            f"{row_count} rows; preserve or migrate them before retrying"
        )


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("goal_allocations"):
        return

    _assert_empty(bind)
    op.drop_table("goal_allocations")


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("goal_allocations"):
        return

    op.create_table(
        "goal_allocations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("target_percentage", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["goal_id"],
            ["goals.id"],
            name="goal_allocations_goal_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="goal_allocations_pkey"),
    )
    op.create_index(
        "ix_goal_allocations_id",
        "goal_allocations",
        ["id"],
        unique=False,
    )
