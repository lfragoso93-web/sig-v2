"""
add_additional_indexes

Revision ID: 023
Revises: 022
Create Date: 2026-07-02

Adiciona o índice composto que ainda NÃO existe no schema:
- dividends (ticker, payment_date DESC): otimiza consultas de proventos
  filtradas por ticker e ordenadas por data de pagamento.

NOTA IMPORTANTE — validação de schema real:
Os demais índices propostos na análise já foram implementados pelo projeto
(Sprint 5B / migrations 0020 e 022), portanto NÃO são recriados aqui:
  * asset_prices (asset_id, timestamp DESC) -> idx_ap_asset_ts (migration 0020)
  * fx_rates (pair, rate_date)              -> uq_fx_rates_pair_date (UniqueConstraint)
  * portfolio_snapshots (portfolio_id, snapshot_date DESC) -> idx_ps_portfolio_date_desc
  * dividends (portfolio_id, payment_date)  -> idx_div_portfolio_payment_date (migration 022)

Esta migration é linear após a 022 (head anterior), evitando o problema de
múltiplas heads no Alembic.
"""
from alembic import op

revision = '023'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # dividends — índice composto (ticker, payment_date) ainda inexistente.
    # Acelera queries do tipo:
    #   WHERE ticker = X ORDER BY payment_date DESC
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_ticker_payment_date "
        "ON dividends (ticker, payment_date DESC) "
        "WHERE payment_date IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_div_ticker_payment_date;")
