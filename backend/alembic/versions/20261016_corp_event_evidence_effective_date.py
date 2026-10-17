"""Persist effective date in corporate-event reconciliation evidence.

Revision ID: 20261016_corp_ev_effective_date
Revises: 20261016_corp_eff_null
Create Date: 2026-10-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261016_corp_ev_effective_date"
down_revision: str | None = "20261016_corp_eff_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "corporate_event_reconciliation_evidence",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column(
        "corporate_event_reconciliation_evidence",
        "effective_date",
    )
