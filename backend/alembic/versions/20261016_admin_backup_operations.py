"""persist administrative backup and restore operation status

Revision ID: 20261016_admin_backup_operations
Revises: 20261010_b3_calendar_config
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261016_admin_backup_operations"
down_revision: str | None = "20261010_b3_calendar_config"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


operation_type = postgresql.ENUM(
    "BACKUP", "RESTORE", name="admin_backup_operation_type", create_type=False
)
operation_status = postgresql.ENUM(
    "queued", "running", "succeeded", "failed",
    name="admin_backup_operation_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    operation_type.create(bind, checkfirst=True)
    operation_status.create(bind, checkfirst=True)
    op.create_table(
        "admin_backup_operations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("operation_type", operation_type, nullable=False),
        sa.Column("status", operation_status, nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("backup_filename", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_admin_backup_operations_created_at",
        "admin_backup_operations", ["created_at"],
    )
    op.create_index(
        "idx_admin_backup_operations_status",
        "admin_backup_operations", ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_admin_backup_operations_status", table_name="admin_backup_operations"
    )
    op.drop_index(
        "idx_admin_backup_operations_created_at", table_name="admin_backup_operations"
    )
    op.drop_table("admin_backup_operations")
    operation_status.drop(op.get_bind(), checkfirst=True)
    operation_type.drop(op.get_bind(), checkfirst=True)
