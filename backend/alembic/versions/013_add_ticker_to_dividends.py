"""re-add ticker column to dividends

Revision ID: 013
Revises: 012
Create Date: 2026-06-23

A migration 003 removeu a coluna ticker da tabela dividends durante a
refatoracao para asset_dividends. Porem portfolio_service ainda usa
dividends.ticker em sum_dividends_for_tickers e sum_dividends_by_ticker.

Esta migration re-adiciona ticker como VARCHAR(100) nullable com index,
permitindo que proventos existentes (asset_dividend_id) possam ser
identificados por ticker via JOIN ou coluna denormalizada.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'dividends',
        sa.Column('ticker', sa.String(100), nullable=True),
    )
    op.create_index('ix_dividends_ticker', 'dividends', ['ticker'])

    # Preenche ticker a partir de asset_dividends -> assets para registros existentes
    op.execute("""
        UPDATE dividends d
        SET ticker = a.ticker
        FROM asset_dividends ad
        JOIN assets a ON a.id = ad.asset_id
        WHERE d.asset_dividend_id = ad.id
          AND d.ticker IS NULL
    """)


def downgrade() -> None:
    op.drop_index('ix_dividends_ticker', table_name='dividends')
    op.drop_column('dividends', 'ticker')
