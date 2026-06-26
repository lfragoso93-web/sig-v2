"""011 - add daily_liquidity to fixed_income_investments

Revision ID: 011
Revises: 010
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'fixed_income_investments',
        sa.Column('daily_liquidity', sa.Boolean(), nullable=False, server_default='false'),
    )
    # Garante consistência: se daily_liquidity=True, date_maturity deve ser NULL
    # (a constraint de negócio é aplicada no service, não em DB para flexibilidade)


def downgrade() -> None:
    op.drop_column('fixed_income_investments', 'daily_liquidity')
