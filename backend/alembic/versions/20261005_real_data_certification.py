"""persist real-data certification event log

Revision ID: 20261005_real_data_cert
Revises: 20260922_corp_ev_ledger_basis
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261005_real_data_cert"
down_revision: str = "20260922_corp_ev_ledger_basis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    evidence_payload_type = sa.JSON().with_variant(
        postgresql.JSONB(),
        "postgresql",
    )
    op.create_table(
        "real_data_certification_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("branch", sa.String(length=100), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("dataset_reference", sa.Text(), nullable=False),
        sa.Column("alembic_revision", sa.String(length=64), nullable=False),
        sa.Column(
            "gate_issue_reference",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "pull_request_reference",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column("evidence_sha256", sa.String(length=64), nullable=False),
        sa.Column("evidence_payload", evidence_payload_type, nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("supersedes_event_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "action IN ('PROMOTE', 'REVOKE')",
            name="ck_real_data_cert_events_action",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_event_id"],
            ["real_data_certification_events.id"],
            name="fk_real_data_cert_events_supersedes",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_real_data_certification_events",
        ),
        sa.UniqueConstraint(
            "event_key",
            name="uq_real_data_certification_events_event_key",
        ),
    )
    op.create_index(
        "ix_real_data_cert_events_environment_created_at",
        "real_data_certification_events",
        ["environment", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_real_data_cert_events_environment_created_at",
        table_name="real_data_certification_events",
    )
    op.drop_table("real_data_certification_events")
