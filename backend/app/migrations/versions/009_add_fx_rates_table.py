"""add fx_rates table

Revision ID: 009
Down revision: 008
Create Date: 2026-06-23

Cria a tabela fx_rates para cache persistente de cotacoes de pares de moeda
(ex: USD-BRL). Evita chamadas repetidas a BRAPI para datas historicas cuja
cotacao nunca muda (PTAX e definitiva no dia seguinte ao pregao).

A coluna rate_date + pair tem constraint UNIQUE para garantir idempotencia
em upserts.
"""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'fx_rates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('pair', sa.String(10), nullable=False),
        sa.Column('rate_date', sa.Date(), nullable=False),
        sa.Column('rate', sa.Numeric(18, 8), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('pair', 'rate_date', name='uq_fx_rates_pair_date'),
    )
    op.create_index('ix_fx_rates_pair_date', 'fx_rates', ['pair', 'rate_date'])


def downgrade():
    op.drop_index('ix_fx_rates_pair_date', table_name='fx_rates')
    op.drop_table('fx_rates')
