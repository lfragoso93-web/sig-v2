"""
add_performance_indexes

Revision ID: 0020
Revises: 015
Create Date: 2026-06-30

Adiciona indices compostos nas tabelas de maior volume do SIG para reduzir
full-scans nas queries mais frequentes. Parte do Sprint 8 (Issue #83).

Indices criados
---------------
Tabela lancamentos:
  idx_lanc_portfolio_date  (portfolio_id, date DESC)
  idx_lanc_portfolio_type  (portfolio_id, asset_type)
  idx_lanc_ticker_date     (ticker, date DESC)

Tabela cotacoes_historicas:
  idx_cotacao_ticker_date  (ticker, date DESC)

Tabela portfolio_class_targets:
  idx_targets_portfolio    (portfolio_id)

Tabela proventos:
  idx_prov_portfolio_date  (portfolio_id, payment_date DESC)
  idx_prov_ticker          (ticker)

NOTA: Usa CREATE INDEX CONCURRENTLY para nao bloquear escrita em producao.
Alembic nao suporta CONCURRENTLY via op.create_index; usando op.execute().
A funcao downgrade remove todos via DROP INDEX.
"""
from alembic import op

# revision identifiers
revision = '0020'
down_revision = '015'   # fix: era '0019', corrigido para '015' (ultima migration real)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # lancamentos
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lanc_portfolio_date
        ON lancamentos (portfolio_id, date DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lanc_portfolio_type
        ON lancamentos (portfolio_id, asset_type);
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_lanc_ticker_date
        ON lancamentos (ticker, date DESC);
        """
    )

    # ------------------------------------------------------------------
    # cotacoes_historicas
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_cotacao_ticker_date
        ON cotacoes_historicas (ticker, date DESC);
        """
    )

    # ------------------------------------------------------------------
    # portfolio_class_targets
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_targets_portfolio
        ON portfolio_class_targets (portfolio_id);
        """
    )

    # ------------------------------------------------------------------
    # proventos
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prov_portfolio_date
        ON proventos (portfolio_id, payment_date DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prov_ticker
        ON proventos (ticker);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_lanc_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_lanc_portfolio_type;")
    op.execute("DROP INDEX IF EXISTS idx_lanc_ticker_date;")
    op.execute("DROP INDEX IF EXISTS idx_cotacao_ticker_date;")
    op.execute("DROP INDEX IF EXISTS idx_targets_portfolio;")
    op.execute("DROP INDEX IF EXISTS idx_prov_portfolio_date;")
    op.execute("DROP INDEX IF EXISTS idx_prov_ticker;")
