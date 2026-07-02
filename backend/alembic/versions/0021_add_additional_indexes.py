"""
add_additional_indexes

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-02

Adiciona índices adicionais para otimizar queries frequentes:
- price_history: para consultas de histórico de preços por ticker e data
- fx_rates: para conversões de moeda por par e data
- portfolio_snapshot: para consultas de snapshots por portfolio e data
"""
from alembic import op

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # price_history — otimiza buscas de histórico de preços
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_ticker_date "
        "ON price_history (ticker, date DESC);"
    )
    
    # fx_rates — otimiza conversões de moeda
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fx_rates_pair_date "
        "ON fx_rates (from_currency, to_currency, date DESC);"
    )
    
    # portfolio_snapshot — otimiza consultas de snapshots históricos
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_portfolio_snapshot_portfolio_date "
        "ON portfolio_snapshot (portfolio_id, snapshot_date DESC);"
    )
    
    # dividends — adiciona índice por ticker e data de pagamento
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_ticker_date "
        "ON dividends (ticker, date_payment DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_price_history_ticker_date;")
    op.execute("DROP INDEX IF EXISTS idx_fx_rates_pair_date;")
    op.execute("DROP INDEX IF EXISTS idx_portfolio_snapshot_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_div_ticker_date;")
