"""add daily return fields to portfolio snapshots

Revision ID: 20260713_snapshot_returns
Revises: 20260712_asset_aliases
"""
from alembic import op
import sqlalchemy as sa

revision = "20260713_snapshot_returns"
down_revision = "20260712_asset_aliases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "net_external_flow",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "dividends_day",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "dividends_accumulated",
            sa.Numeric(18, 2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "daily_return_pct",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "accumulated_return_pct",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "has_partial_prices",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "portfolio_snapshots",
        sa.Column(
            "return_is_estimated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade() -> None:
    op.drop_column("portfolio_snapshots", "return_is_estimated")
    op.drop_column("portfolio_snapshots", "has_partial_prices")
    op.drop_column("portfolio_snapshots", "accumulated_return_pct")
    op.drop_column("portfolio_snapshots", "daily_return_pct")
    op.drop_column("portfolio_snapshots", "dividends_accumulated")
    op.drop_column("portfolio_snapshots", "dividends_day")
    op.drop_column("portfolio_snapshots", "net_external_flow")
