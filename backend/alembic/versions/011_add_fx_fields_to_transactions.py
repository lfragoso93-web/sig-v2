"""add fx_rate and price_brl to transactions

Revision ID: 011
Revises: 010
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'transactions',
        sa.Column('fx_rate', sa.Numeric(18, 8), nullable=True),
    )
    op.add_column(
        'transactions',
        sa.Column('price_brl', sa.Numeric(18, 8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('transactions', 'price_brl')
    op.drop_column('transactions', 'fx_rate')
