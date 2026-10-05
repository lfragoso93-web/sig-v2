"""persist corporate event reconciliation evidence

Revision ID: 20260917_corp_event_recon_ev
Revises: 20260911_rate_annual_comment
Create Date: 2026-09-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260917_corp_event_recon_ev"
down_revision: str = "20260911_rate_annual_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "corporate_event_reconciliation_evidence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("corporate_event_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("fractional_policy", sa.String(length=40), nullable=False),
        sa.Column(
            "fractional_quantity",
            sa.Numeric(precision=24, scale=12),
            nullable=True,
        ),
        sa.Column(
            "fractional_settlement_price",
            sa.Numeric(precision=24, scale=8),
            nullable=True,
        ),
        sa.Column("cash_treatment", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["corporate_event_id"],
            ["corporate_events.id"],
            name="fk_corp_event_recon_evidence_event",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_corporate_event_reconciliation_evidence",
        ),
        sa.UniqueConstraint(
            "corporate_event_id",
            name="uq_corporate_event_reconciliation_evidence_event",
        ),
    )
    op.create_index(
        "ix_corporate_event_reconciliation_evidence_corporate_event_id",
        "corporate_event_reconciliation_evidence",
        ["corporate_event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_corporate_event_reconciliation_evidence_corporate_event_id",
        table_name="corporate_event_reconciliation_evidence",
    )
    op.drop_table("corporate_event_reconciliation_evidence")
