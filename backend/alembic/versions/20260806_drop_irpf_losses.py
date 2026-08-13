"""contract unused legacy monthly IRPF losses table

Revision ID: 20260806_drop_irpf_losses
Revises: 20260806_drop_goal_allocations
Create Date: 2026-08-06

The table has no current runtime consumer and was empty in the validated local
PostgreSQL inventory. The contraction is intentionally guarded and reversible.
The shared ``irpfmarket`` enum is preserved because ``irpf_records`` still uses
it until its own isolated decision.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260806_drop_irpf_losses"
down_revision: str = "20260806_drop_goal_allocations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "irpf_losses"


def _assert_empty(bind: sa.engine.Connection) -> None:
    row_count = int(
        bind.execute(sa.text(f'SELECT COUNT(*) FROM "{_TABLE}"')).scalar_one()
    )
    if row_count:
        raise RuntimeError(
            f"physical contraction blocked: {_TABLE} contains {row_count} rows; "
            "inventory and migration decision must be reviewed first"
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(_TABLE):
        return

    _assert_empty(bind)
    op.drop_table(_TABLE)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table(_TABLE):
        return

    irpf_market = postgresql.ENUM(
        "ACOES",
        "DAY_TRADE",
        "FII",
        "ETF",
        "CRIPTO",
        "RENDA_FIXA",
        "STOCKS",
        name="irpfmarket",
        create_type=False,
    )

    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("market", irpf_market, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column(
            "accumulated_loss",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_irpf_losses_id", _TABLE, ["id"], unique=False)
