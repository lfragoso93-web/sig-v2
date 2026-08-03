"""create dividends sync jobs table

Revision ID: 20260728_dividends_sync_jobs
Revises: 20260724_merge_heads
Create Date: 2026-07-28

Materializa no esquema Alembic a tabela técnica já declarada pelo ORM e
classificada como reconstruível no inventário de pré-produção.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_dividends_sync_jobs"
down_revision: str = "20260724_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dividends_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="idle",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_cursor_date", sa.Date(), nullable=True),
        sa.Column("last_run_assets_processed", sa.Integer(), nullable=True),
        sa.Column("last_run_events_created", sa.Integer(), nullable=True),
        sa.Column("last_run_events_updated", sa.Integer(), nullable=True),
        sa.Column("last_run_errors", sa.Integer(), nullable=True),
        sa.Column("locked_by", sa.String(length=255), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_dividends_sync_jobs_job_name",
        "dividends_sync_jobs",
        ["job_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dividends_sync_jobs_job_name",
        table_name="dividends_sync_jobs",
    )
    op.drop_table("dividends_sync_jobs")
