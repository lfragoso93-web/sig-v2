"""harden system config/fixed income timestamps as not null

Revision ID: 20260807_config_fixed_ts_nn
Revises: 20260807_users_portfolios_ts_nn
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260807_config_fixed_ts_nn"
down_revision: str = "20260807_users_portfolios_ts_nn"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("system_configs", "fixed_income_investments")
_COLUMNS = ("created_at", "updated_at")


def _assert_no_nulls(table: str, column: str) -> None:
    bind = op.get_bind()
    nulls = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")).scalar_one()
    if nulls:
        raise RuntimeError(f"cannot harden {table}.{column}: found {nulls} NULL rows")


def upgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            _assert_no_nulls(table, column)
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
            )


def downgrade() -> None:
    for table in reversed(_TABLES):
        for column in _COLUMNS:
            op.alter_column(
                table,
                column,
                existing_type=sa.DateTime(timezone=True),
                nullable=True,
            )
