"""allow unresolved provider events to keep effective date unknown

Revision ID: 20261016_corp_eff_null
Revises: 20261016_admin_backup_operations
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261016_corp_eff_null"
down_revision: str | None = "20261016_admin_backup_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "corporate_events",
        "effective_date",
        existing_type=sa.Date(),
        nullable=True,
    )


def downgrade() -> None:
    # Refuse to invent dates if unresolved events were persisted while nullable.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM corporate_events WHERE effective_date IS NULL
            ) THEN
                RAISE EXCEPTION
                    'cannot restore NOT NULL: unresolved corporate events exist';
            END IF;
        END $$;
        """
    )
    op.alter_column(
        "corporate_events",
        "effective_date",
        existing_type=sa.Date(),
        nullable=False,
    )
