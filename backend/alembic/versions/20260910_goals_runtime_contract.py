"""align goals table with runtime contract

Revision ID: 20260910_goals_runtime
Revises: 20260820_dividend_occurrence
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260910_goals_runtime"
down_revision: str = "20260820_dividend_occurrence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE goals
            ADD COLUMN IF NOT EXISTS current_value DOUBLE PRECISION NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS base_value DOUBLE PRECISION NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS monthly_contribution DOUBLE PRECISION
        """
    )
    op.execute(
        """
        ALTER TABLE goals
        ALTER COLUMN goal_type TYPE VARCHAR
        USING CASE goal_type::text
            WHEN 'PATRIMONIO_ALVO' THEN 'PATRIMONIO'
            WHEN 'DY_MENSAL' THEN 'PROVENTOS'
            WHEN 'APORTE_MENSAL' THEN 'LIVRE'
            WHEN 'ALOCACAO' THEN 'LIVRE'
            ELSE goal_type::text
        END
        """
    )
    op.execute("ALTER TABLE goals ALTER COLUMN goal_type SET DEFAULT 'LIVRE'")
    op.execute("ALTER TABLE goals ALTER COLUMN current_value DROP DEFAULT")
    op.execute("ALTER TABLE goals ALTER COLUMN base_value DROP DEFAULT")


def downgrade() -> None:
    bind = op.get_bind()
    invalid = int(
        bind.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM goals
                WHERE goal_type NOT IN (
                    'PATRIMONIO_ALVO',
                    'ALOCACAO',
                    'DY_MENSAL',
                    'RENTABILIDADE',
                    'APORTE_MENSAL'
                )
                """
            )
        ).scalar_one()
    )
    if invalid:
        raise RuntimeError(
            "cannot downgrade goals.goal_type: rows use runtime goal types"
        )

    op.execute("ALTER TABLE goals ALTER COLUMN goal_type DROP DEFAULT")
    op.drop_column("goals", "monthly_contribution")
    op.drop_column("goals", "base_value")
    op.drop_column("goals", "current_value")
