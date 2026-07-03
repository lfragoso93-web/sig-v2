"""
add_fx_rate_indexes

Revision ID: 025
Revises: 024
Create Date: 2026-07-02

Adiciona índices de performance para a tabela fx_rates:
- fx_rates (pair, rate_date DESC): otimiza buscas da cotação mais recente por par
- Complementa o UniqueConstraint (pair, rate_date) que é primária mas não otimiza DESC

Esta migration é linear após a 024, mantendo a cadeia consistente no Alembic.
"""
from alembic import op

revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fx_rates — índice composto (pair, rate_date DESC) para buscar taxa mais recente
    # Acelerá queries do tipo: WHERE pair = X ORDER BY rate_date DESC LIMIT 1
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_fx_pair_date_desc "
        "ON fx_rates (pair, rate_date DESC) "
        "WHERE rate_date IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fx_pair_date_desc;")
