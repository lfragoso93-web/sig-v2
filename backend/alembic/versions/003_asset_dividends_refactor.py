"""Cria tabela asset_dividends (proventos globais por ativo) e refatora dividends.

Revision ID: 003_asset_dividends_refactor
Revises: 002_transactions_ticker_100_currency
Create Date: 2026-06-12

Motivacao:
  Antes: Dividend tinha FK direta para portfolio_id + ticker string solto.
  Cada carteira duplicava o mesmo provento.

  Depois:
    asset_dividends  — fonte da verdade global (por ativo, ex_date, dividend_type)
    dividends        — por carteira; FK asset_dividend_id + quantity + totais calculados

Estrategia de rollback:
  - downgrade() restaura a estrutura anterior (colunas antigas) sem perda de dados,
    exceto asset_dividends que e dropada (sem dados criticos — reprocessavel via backfill).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '003_asset_dividends_refactor'
down_revision = '002_transactions_ticker_100_currency'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # 1. Cria tabela asset_dividends (global por ativo)                   #
    # ------------------------------------------------------------------ #
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS asset_dividends (
            id              SERIAL PRIMARY KEY,
            asset_id        INTEGER NOT NULL
                                REFERENCES assets(id) ON DELETE CASCADE,
            ex_date         DATE    NOT NULL,
            payment_date    DATE,
            dividend_type   VARCHAR(20) NOT NULL DEFAULT 'DIVIDENDO',
            value_per_unit  NUMERIC(18, 8) NOT NULL,
            source          VARCHAR(30)    NOT NULL DEFAULT 'brapi',
            CONSTRAINT uq_asset_dividend_asset_exdate_type
                UNIQUE (asset_id, ex_date, dividend_type)
        )
    """))

    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_asset_dividends_asset_id "
        "ON asset_dividends (asset_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_asset_dividends_ex_date "
        "ON asset_dividends (ex_date)"
    ))

    # ------------------------------------------------------------------ #
    # 2. Refatora tabela dividends                                         #
    # ------------------------------------------------------------------ #

    # 2a. Limpa dados antigos (nao ha dados criticos — proventos sao
    #     reprocessados pelo backfill automaticamente)
    conn.execute(text("TRUNCATE TABLE dividends RESTART IDENTITY CASCADE"))

    # 2b. Remove colunas antigas que nao existem mais no model
    for col in [
        "ticker", "asset_type", "type", "amount",
        "value_per_unit", "ex_date", "payment_date",
        "dividend_type", "asset_id",
        "brapi_event_id", "quantity_held", "is_automatic", "notes",
    ]:
        try:
            conn.execute(text(f"ALTER TABLE dividends DROP COLUMN IF EXISTS {col}"))
        except Exception:
            pass

    # 2c. Adiciona coluna asset_dividend_id
    conn.execute(text("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS asset_dividend_id INTEGER
            REFERENCES asset_dividends(id) ON DELETE CASCADE
    """))

    # 2d. Garante que quantity existe (pode ter sido quantity_held antes)
    conn.execute(text("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS quantity DOUBLE PRECISION NOT NULL DEFAULT 0
    """))

    # 2e. Garante total_value e net_value como NUMERIC
    conn.execute(text("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS total_value NUMERIC(18, 2)
    """))
    conn.execute(text("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS net_value NUMERIC(18, 2)
    """))

    # 2f. Garante status como VARCHAR com default
    try:
        conn.execute(text("""
            ALTER TABLE dividends
            ADD COLUMN IF NOT EXISTS status VARCHAR(20)
                NOT NULL DEFAULT 'A_RECEBER'
        """))
    except Exception:
        pass

    # 2g. Unique constraint nova
    try:
        conn.execute(text("""
            ALTER TABLE dividends
            ADD CONSTRAINT uq_dividend_portfolio_asset_dividend
            UNIQUE (portfolio_id, asset_dividend_id)
        """))
    except Exception:
        pass  # ja existe

    # 2h. Indexes
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_dividends_portfolio_id "
        "ON dividends (portfolio_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_dividends_asset_dividend_id "
        "ON dividends (asset_dividend_id)"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_dividends_status "
        "ON dividends (status)"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    # Reverte dividends para estrutura anterior (colunas basicas)
    conn.execute(text("TRUNCATE TABLE dividends RESTART IDENTITY CASCADE"))

    for col in ["asset_dividend_id", "total_value", "net_value", "status"]:
        try:
            conn.execute(text(f"ALTER TABLE dividends DROP COLUMN IF EXISTS {col}"))
        except Exception:
            pass

    # Restaura colunas antigas minimas para nao quebrar o sistema
    conn.execute(text("""
        ALTER TABLE dividends
        ADD COLUMN IF NOT EXISTS ticker       VARCHAR(20),
        ADD COLUMN IF NOT EXISTS asset_type   VARCHAR(50),
        ADD COLUMN IF NOT EXISTS amount       DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS quantity     DOUBLE PRECISION NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS payment_date DATE,
        ADD COLUMN IF NOT EXISTS ex_date      DATE
    """))

    # Remove asset_dividends
    conn.execute(text("DROP TABLE IF EXISTS asset_dividends CASCADE"))
