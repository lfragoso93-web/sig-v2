"""add dividends table

Revision ID: 003
Down revision: 002
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'dividends',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('portfolio_id', sa.Integer(), sa.ForeignKey('portfolios.id', ondelete='CASCADE'), nullable=False),
        sa.Column('asset_id', sa.Integer(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dividend_type', sa.String(20), nullable=False, server_default='DIVIDENDO'),
        sa.Column('status', sa.String(20), nullable=False, server_default='A_RECEBER'),
        sa.Column('ex_date', sa.Date(), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=True),
        sa.Column('quantity', sa.Numeric(18, 8), nullable=False),
        sa.Column('value_per_unit', sa.Numeric(18, 8), nullable=False),
        sa.Column('total_value', sa.Numeric(18, 8), nullable=False),
        sa.Column('net_value', sa.Numeric(18, 8), nullable=False),
    )
    op.create_index('ix_dividends_portfolio_id', 'dividends', ['portfolio_id'])
    op.create_index('ix_dividends_asset_portfolio_ex', 'dividends', ['asset_id', 'portfolio_id', 'ex_date'], unique=True)


def downgrade():
    op.drop_table('dividends')
