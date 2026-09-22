"""add ledger basis to corporate event reconciliation evidence

Revision ID: 20260922_corp_ev_ledger_basis
Revises: 20260917_corp_event_recon_ev
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_corp_ev_ledger_basis"
down_revision: str = "20260917_corp_event_recon_ev"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "corporate_event_reconciliation_evidence",
        sa.Column("ledger_basis", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "corporate_event_reconciliation_evidence",
        sa.Column("ledger_transformation_reference", sa.Text(), nullable=True),
    )
    op.add_column(
        "corporate_event_reconciliation_evidence",
        sa.Column(
            "ledger_quantity_factor",
            sa.Numeric(precision=24, scale=12),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "corporate_event_reconciliation_evidence",
        "ledger_quantity_factor",
    )
    op.drop_column(
        "corporate_event_reconciliation_evidence",
        "ledger_transformation_reference",
    )
    op.drop_column(
        "corporate_event_reconciliation_evidence",
        "ledger_basis",
    )
