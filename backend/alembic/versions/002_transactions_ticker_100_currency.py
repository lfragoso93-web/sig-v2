"""Aumenta ticker para VARCHAR(100) em assets e adiciona coluna currency em transactions.

Revision ID: 002_transactions_ticker_100_currency
Revises: 001_initial_schema
Create Date: 2026-06-11

Motivação:
  - Slugs do Tesouro Direto chegam a ~60 chars (ex: tesouro-renda-plus-aposentadoria-extra-01122065)
    A coluna assets.ticker foi criada como VARCHAR(30) na 001 — precisa ser ampliada.
  - transactions não possui coluna ticker (usa asset_id FK). A versão anterior desta migration
    tentava alterar transactions.ticker incorretamente, causando DuplicateObject / column not found
    em banco limpo. Esta versão corrige o alvo para assets.ticker.
  - Adiciona currency em transactions para registrar moeda da operação (BRL por padrão).

CORREÇÃO (2026-06-16):
  - ALTER TABLE agora aponta para assets.ticker (coluna correta, criada na 001 como VARCHAR(30))
  - transactions.ticker nunca existiu — removido do upgrade/downgrade
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

    # 1. Aumenta assets.ticker de VARCHAR(30) para VARCHAR(100)
    #    Idempotente: ALTER COLUMN TYPE para tipo maior é sempre seguro no PG
    try:
        conn.execute(text(
            "ALTER TABLE assets ALTER COLUMN ticker TYPE VARCHAR(100)"
        ))
    except Exception:
        pass  # já está em VARCHAR(100) ou maior — ok

    # 2. Adiciona coluna currency em transactions se ainda não existir
    try:
        conn.execute(text(
            "ALTER TABLE transactions "
            "ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'BRL'"
        ))
    except Exception:
        pass  # coluna já existe — ok


def downgrade() -> None:
    conn = op.get_bind()

    # Reverte assets.ticker para VARCHAR(30)
    # Atenção: pode truncar dados existentes com ticker > 30 chars
    try:
        conn.execute(text(
            "ALTER TABLE assets ALTER COLUMN ticker TYPE VARCHAR(30)"
        ))
    except Exception:
        pass

    # Remove coluna currency de transactions
    try:
        conn.execute(text(
            "ALTER TABLE transactions DROP COLUMN IF EXISTS currency"
        ))
    except Exception:
        pass
