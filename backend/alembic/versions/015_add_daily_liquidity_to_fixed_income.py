"""015_add_daily_liquidity_to_fixed_income

Revision ID: 015
Revises: 014
Create Date: 2026-06-29

Adiciona coluna daily_liquidity (BOOLEAN NOT NULL DEFAULT FALSE)
à tabela fixed_income_investments.

A coluna existia no model SQLAlchemy mas estava ausente no banco,
causando UndefinedColumnError ao tentar salvar lançamentos de Renda Fixa.
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'fixed_income_investments',
        sa.Column(
            'daily_liquidity',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('FALSE'),
            comment='Se TRUE o título pode ser resgatado a qualquer dia (sem vencimento relevante)',
        ),
    )


def downgrade() -> None:
    op.drop_column('fixed_income_investments', 'daily_liquidity')
