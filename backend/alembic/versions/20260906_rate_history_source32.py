"""widen rate history source provenance

Revision ID: 20260906_rate_source32
Revises: 20260906_rate_coverage
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_rate_source32"
down_revision: str = "20260906_rate_coverage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "rate_history",
        "source",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    too_long = bind.execute(
        sa.text("SELECT COUNT(*) FROM rate_history WHERE length(source) > 20")
    ).scalar_one()
    if int(too_long):
        raise RuntimeError(
            "cannot downgrade rate_history.source to VARCHAR(20): "
            "rows with longer provenance exist"
        )

    op.alter_column(
        "rate_history",
        "source",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
