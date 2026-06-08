"""add fx fields to transactions

Revision ID: 004
Down revision: 003
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('transactions', sa.Column('currency', sa.String(3), nullable=False, server_default='BRL'))
    op.add_column('transactions', sa.Column('fx_rate', sa.Numeric(18, 8), nullable=True))  # cotacao USD/BRL
    op.add_column('transactions', sa.Column('price_brl', sa.Numeric(18, 8), nullable=True))  # preco em BRL (usado nos calculos)


def downgrade():
    op.drop_column('transactions', 'price_brl')
    op.drop_column('transactions', 'fx_rate')
    op.drop_column('transactions', 'currency')
