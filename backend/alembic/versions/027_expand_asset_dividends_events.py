"""
expand_asset_dividends_events

Revision ID: 027
Revises: 026
Create Date: 2026-07-03

Expande asset_dividends para armazenar Data Com e campos completos dos
eventos de proventos/corporativos retornados pela BRAPI.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '027'
down_revision = '026'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dividendtype') THEN
                ALTER TYPE dividendtype ADD VALUE IF NOT EXISTS 'SUBSCRICAO';
            END IF;
        END $$;
        """)

    raw_payload_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')

    op.add_column('asset_dividends', sa.Column('record_date', sa.Date(), nullable=True))
    op.add_column('asset_dividends', sa.Column('approved_on', sa.Date(), nullable=True))
    op.add_column('asset_dividends', sa.Column('gross_value_per_unit', sa.Numeric(18, 8), nullable=True))
    op.add_column('asset_dividends', sa.Column('factor', sa.Numeric(24, 12), nullable=True))
    op.add_column('asset_dividends', sa.Column('complete_factor', sa.Numeric(24, 12), nullable=True))
    op.add_column('asset_dividends', sa.Column('isin_code', sa.String(length=32), nullable=True))
    op.add_column('asset_dividends', sa.Column('asset_issued', sa.String(length=32), nullable=True))
    op.add_column('asset_dividends', sa.Column('related_to', sa.String(length=80), nullable=True))
    op.add_column('asset_dividends', sa.Column('remarks', sa.Text(), nullable=True))
    op.add_column('asset_dividends', sa.Column('raw_payload', raw_payload_type, nullable=True))

    op.create_index('ix_asset_dividends_record_date', 'asset_dividends', ['record_date'], unique=False)
    op.create_index('ix_asset_dividends_approved_on', 'asset_dividends', ['approved_on'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_asset_dividends_approved_on', table_name='asset_dividends')
    op.drop_index('ix_asset_dividends_record_date', table_name='asset_dividends')

    op.drop_column('asset_dividends', 'raw_payload')
    op.drop_column('asset_dividends', 'remarks')
    op.drop_column('asset_dividends', 'related_to')
    op.drop_column('asset_dividends', 'asset_issued')
    op.drop_column('asset_dividends', 'isin_code')
    op.drop_column('asset_dividends', 'complete_factor')
    op.drop_column('asset_dividends', 'factor')
    op.drop_column('asset_dividends', 'gross_value_per_unit')
    op.drop_column('asset_dividends', 'approved_on')
    op.drop_column('asset_dividends', 'record_date')
