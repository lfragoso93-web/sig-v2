"""remove duplicate legacy rate_history unique index

Revision ID: 20260807_drop_dup_rate_idx
Revises: 20260806_drop_irpf_records
Create Date: 2026-08-07

Some preserved databases contain both the canonical unique index created by
migration 014 (``uq_rate_history_indicator_date``) and an ORM-era duplicate
named ``ix_rate_history_indicator_date_unique``.  The duplicate is not part of
the canonical Alembic graph and causes a persistent autogenerate diff.

The upgrade is defensive: it only removes the duplicate when the canonical
index exists, so uniqueness of (indicator, date) is never weakened.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260807_drop_dup_rate_idx"
down_revision: str = "20260806_drop_irpf_records"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'rate_history'
                  AND indexname = 'ix_rate_history_indicator_date_unique'
            ) AND NOT EXISTS (
                SELECT 1
                FROM pg_indexes
                WHERE schemaname = current_schema()
                  AND tablename = 'rate_history'
                  AND indexname = 'uq_rate_history_indicator_date'
            ) THEN
                RAISE EXCEPTION
                    'refusing to drop duplicate rate_history index: canonical unique index is absent';
            END IF;
        END
        $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_rate_history_indicator_date_unique")


def downgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_rate_history_indicator_date_unique
        ON rate_history (indicator, date)
        """
    )
