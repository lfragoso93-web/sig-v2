"""add asset provider metadata

Revision ID: 20260714_asset_provider_metadata
Revises: 20260713_snapshot_returns
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "20260714_asset_provider_metadata"
down_revision = "20260713_snapshot_returns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assets", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("provider_symbol", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("provider_status", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("provider_last_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("assets", sa.Column("provider_last_error", sa.String(), nullable=True))
    op.add_column("assets", sa.Column("provider_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_assets_provider_status", "assets", ["provider_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_assets_provider_status", table_name="assets")
    op.drop_column("assets", "provider_attempts")
    op.drop_column("assets", "provider_last_error")
    op.drop_column("assets", "provider_last_sync_at")
    op.drop_column("assets", "provider_status")
    op.drop_column("assets", "provider_symbol")
    op.drop_column("assets", "provider")
