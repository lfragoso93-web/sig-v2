"""
add_performance_indexes

Revision ID: 0020
Revises: 015
Create Date: 2026-06-30

Adiciona indices compostos baseados no schema REAL apos migrations 001-015.
Parte do Sprint 8 (Issue #83).

Schema auditado:
  transactions (pos-006): portfolio_id, ticker, asset_type, operation, date, quantity, price, fees, currency
  dividends    (pos-013): portfolio_id, ticker, date_payment, date_ex, asset_id
  portfolio_class_targets (008): portfolio_id, asset_type, target_pct
  asset_prices:            asset_id, timestamp
  portfolio_positions:     portfolio_id

NOTA: CREATE INDEX simples (sem CONCURRENTLY) para rodar dentro da transacao Alembic.
"""
from alembic import op

revision = '0020'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # transactions — colunas reais apos migration 006
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_date "
        "ON transactions (portfolio_id, date DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_operation "
        "ON transactions (portfolio_id, operation);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_ticker_date "
        "ON transactions (ticker, date DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_asset_type "
        "ON transactions (asset_type);"
    )

    # asset_prices — colunas originais ainda existentes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ap_asset_ts "
        "ON asset_prices (asset_id, timestamp DESC);"
    )

    # dividends — portfolio_id + date_payment (colunas da 001, ticker adicionado na 013)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_portfolio_date "
        "ON dividends (portfolio_id, date_payment DESC);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_ticker "
        "ON dividends (ticker);"
    )

    # portfolio_class_targets — criada na migration 008
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pct_portfolio "
        "ON portfolio_class_targets (portfolio_id);"
    )

    # portfolio_positions
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pp_portfolio "
        "ON portfolio_positions (portfolio_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_operation;")
    op.execute("DROP INDEX IF EXISTS idx_txn_ticker_date;")
    op.execute("DROP INDEX IF EXISTS idx_txn_asset_type;")
    op.execute("DROP INDEX IF EXISTS idx_ap_asset_ts;")
    op.execute("DROP INDEX IF EXISTS idx_div_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_div_ticker;")
    op.execute("DROP INDEX IF EXISTS idx_pct_portfolio;")
    op.execute("DROP INDEX IF EXISTS idx_pp_portfolio;")
