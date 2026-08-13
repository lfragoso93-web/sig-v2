"""contract unused legacy monthly IRPF records table

Revision ID: 20260806_drop_irpf_records
Revises: 20260806_drop_irpf_losses
Create Date: 2026-08-06

The table has no current runtime consumer and was empty in the validated local
PostgreSQL inventory. The contraction is guarded and reversible. The shared
``irpfmarket`` enum is intentionally preserved for compatibility and downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260806_drop_irpf_records"
down_revision: str = "20260806_drop_irpf_losses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "irpf_records"


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
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("market", irpf_market, nullable=False),
        sa.Column("gross_profit", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("loss_offset", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("taxable_profit", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("ir_rate", sa.Numeric(6, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("ir_due", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("ir_withheld", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("ir_to_pay", sa.Numeric(18, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("is_exempt", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("darf_code", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_irpf_records_id", _TABLE, ["id"], unique=False)
    op.create_index("ix_irpf_records_user_id", _TABLE, ["user_id"], unique=False)
