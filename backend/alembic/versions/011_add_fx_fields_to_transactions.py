"""add fx_rate and price_brl to transactions

Revision ID: 011
Down revision: 010
Create Date: 2026-06-23

Adiciona colunas fx_rate e price_brl na tabela transactions.
  fx_rate   -- cotacao USD/BRL na data da transacao (nullable, usado apenas para ativos em USD)
  price_brl -- preco da transacao convertido para BRL (nullable, calculado pelo backend)
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(
        'transactions',
        sa.Column('fx_rate', sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        'transactions',
        sa.Column('price_brl', sa.Numeric(18, 8), nullable=True),
    )


def downgrade():
    op.drop_column('transactions', 'price_brl')
    op.drop_column('transactions', 'fx_rate')
