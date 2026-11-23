"""add performance query indexes for transactions, assets, positions and corporate events

Revision ID: 20261114_perf_query_indexes
Revises: 20261111_fraction_settlements
Create Date: 2026-11-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261114_perf_query_indexes"
down_revision: str | None = "20261111_fraction_settlements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. transactions (portfolio_id, ticker) - acelera buscas combinadas por carteira e ativo
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_ticker "
        "ON transactions (portfolio_id, ticker);"
    )
    # 2. assets (lower(ticker)) - acelera lookups e cotacoes DB-first case-insensitive
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_assets_lower_ticker "
        "ON assets (lower(ticker));"
    )
    # 3. portfolio_positions (asset_id) - acelera joins e FK checks de posicoes por ativo
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_portfolio_positions_asset_id "
        "ON portfolio_positions (asset_id);"
    )
    # 4. corporate_events (portfolio_id) - acelera queries de eventos por carteira
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_corporate_events_portfolio_id "
        "ON corporate_events (portfolio_id);"
    )
    # 5. corporate_event_destination_legs (corporate_event_id) - acelera joins e cascade em pernas de eventos
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_corp_event_destination_leg_event "
        "ON corporate_event_destination_legs (corporate_event_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_corp_event_destination_leg_event;")
    op.execute("DROP INDEX IF EXISTS ix_corporate_events_portfolio_id;")
    op.execute("DROP INDEX IF EXISTS ix_portfolio_positions_asset_id;")
    op.execute("DROP INDEX IF EXISTS idx_assets_lower_ticker;")
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_ticker;")
