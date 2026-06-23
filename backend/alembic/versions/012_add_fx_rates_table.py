"""add fx_rates table

Revision ID: 012
Revises: 011
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'fx_rates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pair', sa.String(10), nullable=False),
        sa.Column('rate_date', sa.Date(), nullable=False),
        sa.Column('rate', sa.Numeric(18, 8), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint('pair', 'rate_date', name='uq_fx_rates_pair_date'),
    )
    op.create_index('ix_fx_rates_pair_date', 'fx_rates', ['pair', 'rate_date'])


def downgrade() -> None:
    op.drop_index('ix_fx_rates_pair_date', table_name='fx_rates')
    op.drop_table('fx_rates')
