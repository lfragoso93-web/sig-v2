"""drop legacy materialized dividend tables

Revision ID: 20260731_drop_legacy_divs
Revises: 20260729_dividend_identity
Create Date: 2026-07-31

This contraction is intentionally guarded: both legacy tables must be empty
after the approved backup/cleanup workflow. The migration is irreversible
because recreating empty tables would not restore discarded business data.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_drop_legacy_divs"
down_revision: str = "20260729_dividend_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_TABLES = ("dividends", "dividends_sync_jobs")


def _assert_empty(bind: sa.engine.Connection, table_name: str) -> None:
    row_count = int(
        bind.execute(sa.text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
    )
    if row_count:
        raise RuntimeError(
            f"physical contraction blocked: {table_name} contains {row_count} rows; "
            "run the approved backup and cleanup workflow first"
        )


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in _LEGACY_TABLES:
        _assert_empty(bind, table_name)

    op.drop_table("dividends")
    op.drop_table("dividends_sync_jobs")


def downgrade() -> None:
    raise RuntimeError(
        "20260731_drop_legacy_divs is irreversible; restore the approved "
        "pre-contraction backup instead"
    )
