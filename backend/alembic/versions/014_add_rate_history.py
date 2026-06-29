"""014_add_rate_history

Revision ID: 014
Revises: 013
Create Date: 2026-06-28

Cria tabela rate_history para armazenar historico diario/mensal
de indicadores macroeconomicos (CDI, IPCA, SELIC).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'rate_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'indicator',
            sa.String(length=10),
            nullable=False,
            comment='Indicador: CDI | IPCA | SELIC',
        ),
        sa.Column(
            'date',
            sa.Date(),
            nullable=False,
            comment='Data de referencia da taxa',
        ),
        # Taxa diaria efetiva (% a.d.) — ex: 0.04091 para CDI de ~10.5% a.a.
        sa.Column(
            'rate_daily',
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment='Taxa diaria efetiva em % a.d.',
        ),
        # Taxa mensal (% a.m.) — ex: 0.88 para CDI de ~10.5% a.a.
        sa.Column(
            'rate_monthly',
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment='Taxa mensal em % a.m.',
        ),
        # Taxa anual (% a.a.) — ex: 10.5
        sa.Column(
            'rate_annual',
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment='Taxa anual em % a.a.',
        ),
        sa.Column(
            'source',
            sa.String(length=20),
            nullable=False,
            server_default='BCB',
            comment='Fonte: BCB | BRAPI | SEED | MANUAL',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indice unico: um registro por indicador por dia
    op.create_index(
        'uq_rate_history_indicator_date',
        'rate_history',
        ['indicator', 'date'],
        unique=True,
    )

    # Indice em date para queries de range (performance)
    op.create_index(
        'ix_rate_history_date',
        'rate_history',
        ['date'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_rate_history_date', table_name='rate_history')
    op.drop_index('uq_rate_history_indicator_date', table_name='rate_history')
    op.drop_table('rate_history')
