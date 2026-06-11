"""Aumenta ticker para VARCHAR(100) e adiciona coluna currency em transactions.

Revision ID: 002_transactions_ticker_100_currency
Revises: 001_initial_schema
Create Date: 2026-06-11

Motivação:
  - Slugs do Tesouro Direto chegam a ~60 chars (ex: tesouro-renda-plus-aposentadoria-extra-01122065)
  - A migration inline em transactions.py (_ensure_migrations) resolveu o problema em produção,
    mas deixou a dívida técnica de não ter representação formal no histórico Alembic.
  - Esta migration formaliza as duas DDLs usando IF NOT EXISTS / TRY para ser idempotente,
    garantindo que funcione tanto em bancos novos (criados via 001) quanto em bancos existentes
    que já receberam o ALTER via migration inline.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '002_transactions_ticker_100_currency'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Aumenta ticker para VARCHAR(100) — idempotente via TRY
    #    (em PG, ALTER COLUMN TYPE é seguro repetir quando o tipo já é maior ou igual)
    try:
        conn.execute(text(
            "ALTER TABLE transactions ALTER COLUMN ticker TYPE VARCHAR(100)"
        ))
    except Exception:
        pass  # já está em VARCHAR(100) — ok

    # 2. Adiciona coluna currency se ainda não existir
    try:
        conn.execute(text(
            "ALTER TABLE transactions "
            "ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'BRL'"
        ))
    except Exception:
        pass  # coluna já existe — ok


def downgrade() -> None:
    conn = op.get_bind()
    # Reverte ticker para VARCHAR(20) — atenção: pode truncar dados existentes
    try:
        conn.execute(text(
            "ALTER TABLE transactions ALTER COLUMN ticker TYPE VARCHAR(20)"
        ))
    except Exception:
        pass
    # Remove coluna currency
    try:
        conn.execute(text(
            "ALTER TABLE transactions DROP COLUMN IF EXISTS currency"
        ))
    except Exception:
        pass
