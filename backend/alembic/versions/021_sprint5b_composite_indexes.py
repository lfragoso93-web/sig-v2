"""
sprint5b_composite_indexes

Revision ID: 021
Revises: 0020
Create Date: 2026-06-30

Adiciona os índices compostos identificados na auditoria de performance
da Sprint 5B que não foram cobertos pela migration 0020.

Problemas resolvidos:
  1. portfolio_snapshots — padrão de acesso (portfolio_id, snapshot_date DESC)
     usado por _snapshot_at / _snapshot_before_today / _latest_snapshot /
     _first_snapshot sem índice composto, forçando seq scan + sort.

  2. dividends (portfolio_id, ticker) — cobre sum_dividends_by_ticker que
     filtra WHERE portfolio_id=X AND ticker IN (...). Sem este índice, o
     planner usa apenas idx em portfolio_id e ainda faz bitmap heap scan
     em ticker separado.

  3. dividends (portfolio_id, status) — cobre _proventos_total que filtra
     WHERE portfolio_id=X AND status='RECEBIDO'. O índice de portfolio_id
     sozinho deixa o filtro de status como recheck condition.

  4. asset_dividends (asset_id, ex_date DESC) — cobre a consulta de
     proventos por ativo ordenada por data.

  5. transactions (portfolio_id, date ASC, id ASC) — cobre o padrão de
     _get_realized_pnl_by_ticker e _calc_invested_up_to que ordenam por
     (date ASC, id ASC). O índice 0020 tem (portfolio_id, date DESC) —
     adiciona o ascendente para evitar sort reverso.

Todos usam CREATE INDEX IF NOT EXISTS — idempotentes e seguros para re-run.
"""
from alembic import op

revision = '021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. portfolio_snapshots — padrão principal de acesso por período
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ps_portfolio_date_desc "
        "ON portfolio_snapshots (portfolio_id, snapshot_date DESC);"
    )

    # 2. dividends — filtro por carteira + ticker (sum_dividends_by_ticker)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_portfolio_ticker "
        "ON dividends (portfolio_id, ticker);"
    )

    # 3. dividends — filtro por carteira + status (_proventos_total)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_div_portfolio_status "
        "ON dividends (portfolio_id, status);"
    )

    # 4. asset_dividends — histórico de proventos por ativo
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_ad_asset_exdate_desc "
        "ON asset_dividends (asset_id, ex_date DESC);"
    )

    # 5. transactions — ordenação ASC usada por _get_realized_pnl_by_ticker
    #    e _calc_invested_up_to (ORDER BY date ASC, id ASC)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_txn_portfolio_date_asc "
        "ON transactions (portfolio_id, date ASC, id ASC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_ps_portfolio_date_desc;")
    op.execute("DROP INDEX IF EXISTS idx_div_portfolio_ticker;")
    op.execute("DROP INDEX IF EXISTS idx_div_portfolio_status;")
    op.execute("DROP INDEX IF EXISTS idx_ad_asset_exdate_desc;")
    op.execute("DROP INDEX IF EXISTS idx_txn_portfolio_date_asc;")
