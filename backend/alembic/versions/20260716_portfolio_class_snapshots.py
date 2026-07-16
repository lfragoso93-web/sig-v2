"""add portfolio class snapshots

Revision ID: 20260716_portfolio_class_snapshots
Revises: 20260714_asset_provider_metadata
Create Date: 2026-07-16
"""
from alembic import op
import sqlalchemy as sa

revision = "20260716_portfolio_class_snapshots"
down_revision = "20260714_asset_provider_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_class_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("market_value", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("cost_basis", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("realized_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("unrealized_pnl", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net_external_flow", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("dividends_day", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("dividends_accumulated", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("daily_return_pct", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("accumulated_return_pct", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("has_partial_prices", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("return_is_estimated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valuation_status", sa.String(length=40), nullable=False, server_default="complete"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_id",
            "asset_type",
            "snapshot_date",
            name="uq_class_snapshot_portfolio_type_date",
        ),
    )
    op.create_index(
        "idx_pcs_portfolio_type_date",
        "portfolio_class_snapshots",
        ["portfolio_id", "asset_type", "snapshot_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_pcs_portfolio_type_date", table_name="portfolio_class_snapshots")
    op.drop_table("portfolio_class_snapshots")
