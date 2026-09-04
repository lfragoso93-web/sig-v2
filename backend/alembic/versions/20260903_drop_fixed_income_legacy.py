"""drop legacy fixed income projection

Revision ID: 20260903_drop_fixed_income
Revises: 20260820_dividend_occurrence

This contraction is intentionally guarded. The legacy projection table must
be empty after the approved backup/export workflow. The migration is
irreversible because recreating an empty table would not restore discarded
business data.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_drop_fixed_income"
down_revision: str = "20260820_dividend_occurrence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "fixed_income_investments"
_ENUM_TYPES = ("fixedincometype", "indexertype")


def _assert_empty(bind: sa.engine.Connection) -> None:
    row_count = int(
        bind.execute(
            sa.text(f'SELECT COUNT(*) FROM "{_TABLE}"')
        ).scalar_one()
    )
    if row_count:
        raise RuntimeError(
            f"physical contraction blocked: {_TABLE} contains "
            f"{row_count} rows; run the approved backup and cleanup "
            "workflow first"
        )


def upgrade() -> None:
    bind = op.get_bind()
    _assert_empty(bind)

    op.drop_table(_TABLE)

    for enum_name in _ENUM_TYPES:
        op.execute(sa.text(f'DROP TYPE IF EXISTS "{enum_name}"'))


def downgrade() -> None:
    raise RuntimeError(
        "20260903_drop_fixed_income is irreversible; restore the approved "
        "pre-contraction backup instead"
    )
