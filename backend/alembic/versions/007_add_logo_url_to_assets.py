"""add logo_url to assets

Revision ID: 007
Revises: 006_tx_ticker_based
Create Date: 2026-06-19

"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = '006_tx_ticker_based'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Usa SQL nativo para garantir idempotência (evita DuplicateColumn se a coluna já existir)
    op.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS logo_url VARCHAR")


def downgrade() -> None:
    op.execute("ALTER TABLE assets DROP COLUMN IF EXISTS logo_url")
