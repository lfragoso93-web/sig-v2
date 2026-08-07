"""align goals schema with the active goals module contract

Revision ID: 20260807_goals_contract
Revises: 20260807_pos_snap_ts_nn
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_goals_contract"
down_revision: str = "20260807_pos_snap_ts_nn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _assert_goals_empty() -> None:
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM goals")).scalar_one()
    if count:
        raise RuntimeError(
            f"cannot migrate goals contract automatically: found {count} existing rows"
        )


def upgrade() -> None:
    _assert_goals_empty()

    op.alter_column(
        "goals",
        "goal_type",
        existing_type=sa.Enum(
            "PATRIMONIO_ALVO",
            "ALOCACAO",
            "DY_MENSAL",
            "RENTABILIDADE",
            "APORTE_MENSAL",
            name="goaltype",
        ),
        type_=sa.String(length=30),
        existing_nullable=False,
        postgresql_using="goal_type::text",
    )
    op.alter_column(
        "goals",
        "target_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="target_date::timestamp with time zone",
    )

    op.add_column(
        "goals",
        sa.Column(
            "current_value",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "goals",
        sa.Column(
            "base_value",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "goals",
        sa.Column("monthly_contribution", sa.Numeric(18, 2), nullable=True),
    )


def downgrade() -> None:
    _assert_goals_empty()

    op.drop_column("goals", "monthly_contribution")
    op.drop_column("goals", "base_value")
    op.drop_column("goals", "current_value")

    op.alter_column(
        "goals",
        "target_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=True,
        postgresql_using="target_date::date",
    )
    op.alter_column(
        "goals",
        "goal_type",
        existing_type=sa.String(length=30),
        type_=sa.Enum(
            "PATRIMONIO_ALVO",
            "ALOCACAO",
            "DY_MENSAL",
            "RENTABILIDADE",
            "APORTE_MENSAL",
            name="goaltype",
            create_type=False,
        ),
        existing_nullable=False,
        postgresql_using="goal_type::goaltype",
    )
