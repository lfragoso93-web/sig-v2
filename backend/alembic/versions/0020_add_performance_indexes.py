"""
add_performance_indexes

Revision ID: 0020
Revises: 015
Create Date: 2026-06-30

Adiciona indices compostos nas tabelas de maior volume do SIG para reduzir
full-scans nas queries mais frequentes. Parte do Sprint 8 (Issue #83).

NOTA: Usa CREATE INDEX simples (sem CONCURRENTLY) para rodar dentro da
transacao Alembic. Para tabelas grandes em producao, recriar manualmente
com CONCURRENTLY apos o deploy.

Tabelas e indices
-----------------
transactions:
  idx_txn_portfolio_date  (portfolio_id, date DESC)
  idx_txn_portfolio_type  (portfolio_id, transaction_type)
  idx_txn_asset_date      (asset_id, date DESC)

asset_prices:
  idx_ap_asset_ts         (asset_id, timestamp DESC)

dividends:
  idx_div_portfolio_date  (portfolio_id, date_payment DESC)
  idx_div_asset           (asset_id)

portfolio_positions:
  idx_pp_portfolio        (portfolio_id)
"""
from alembic import op

revision = '0020'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # transactions
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_date "
        "ON transactions (portfolio_id, date DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_type "
        "ON transactions (portfolio_id, transaction_type);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_asset_date "
        "ON transactions (asset_id, date DESC);"
    )

    # asset_prices
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ap_asset_ts "
        "ON asset_prices (asset_id, timestamp DESC);"
    )

    # dividends
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_portfolio_date "
        "ON dividends (portfolio_id, date_payment DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_asset "
        "ON dividends (asset_id);"
    )

    # portfolio_positions
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pp_portfolio "
        "ON portfolio_positions (portfolio_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_type;")
    op.execute("DROP INDEX IF EXISTS idx_txn_asset_date;")
    op.execute("DROP INDEX IF EXISTS idx_ap_asset_ts;")
    op.execute("DROP INDEX IF EXISTS idx_div_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_div_asset;")
    op.execute("DROP INDEX IF EXISTS idx_pp_portfolio;")
