"""
add_record_date_to_asset_dividends

Revision ID: 027
Revises: 026
Create Date: 2026-07-03

Adiciona record_date em asset_dividends para armazenar a data com
(lastDatePrior na BRAPI), separando-a da data ex.
"""
from alembic import op
import sqlalchemy as sa

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'asset_dividends',
        sa.Column('record_date', sa.Date(), nullable=True),
    )
    op.create_index(
        'ix_asset_dividends_record_date',
        'asset_dividends',
        ['record_date'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_asset_dividends_record_date', table_name='asset_dividends')
    op.drop_column('asset_dividends', 'record_date')
