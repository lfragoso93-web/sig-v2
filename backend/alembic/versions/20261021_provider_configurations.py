"""create provider_configurations table for SuperAdmin dynamic provider management

Revision ID: 20261021_provider_configs
Revises: 20261021_contract_corp_events
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261021_provider_configs"
down_revision: str | None = "20261021_contract_corp_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "provider_configurations"


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.String(length=50), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="10", nullable=False),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("api_key_encrypted", sa.String(length=500), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column("custom_headers", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="PENDING", nullable=False),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", name="uq_provider_configurations_provider_id"),
    )
    op.create_index("ix_provider_configurations_id", _TABLE, ["id"], unique=False)
    op.create_index("ix_provider_configurations_provider_id", _TABLE, ["provider_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_provider_configurations_provider_id", table_name=_TABLE)
    op.drop_index("ix_provider_configurations_id", table_name=_TABLE)
    op.drop_table(_TABLE)
