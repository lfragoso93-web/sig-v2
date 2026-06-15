"""Adiciona last_price e last_price_updated_at na tabela assets.

Revision ID: 004_add_last_price_to_assets
Revises: 003_asset_dividends_refactor
Create Date: 2026-06-15

Motivacao:
  Implementar cache L1 de cotação diretamente no modelo Asset.
  Permite que portfolio_service leia o preco do banco em vez de chamar
  a API externa a cada request, reduzindo consumo de quota BRAPI/yfinance.

  - last_price              : ultimo preco conhecido (NUMERIC 18,8, nullable)
  - last_price_updated_at   : timestamp da ultima atualizacao (TIMESTAMPTZ, nullable)

  Ambos iniciam como NULL (sem dado) para todos os ativos existentes.
  O scheduler e o fluxo on-demand populam esses campos apos a primeira busca.

Rollback:
  downgrade() remove as duas colunas sem perda de dados criticos
  (sao cache reconstruivel via scheduler ou on-demand).
"""
from alembic import op
import sqlalchemy as sa

revision = '004_add_last_price_to_assets'
down_revision = '003_asset_dividends_refactor'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'assets',
        sa.Column(
            'last_price',
            sa.Numeric(precision=18, scale=8),
            nullable=True,
            comment='Ultimo preco conhecido (cache L1). Nunca usar como fallback de PM.',
        ),
    )
    op.add_column(
        'assets',
        sa.Column(
            'last_price_updated_at',
            sa.DateTime(timezone=True),
            nullable=True,
            comment='Timestamp da ultima atualizacao de last_price.',
        ),
    )
    # Index para queries de ativos com preco desatualizado (scheduler)
    op.create_index(
        'ix_assets_last_price_updated_at',
        'assets',
        ['last_price_updated_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_assets_last_price_updated_at', table_name='assets')
    op.drop_column('assets', 'last_price_updated_at')
    op.drop_column('assets', 'last_price')
