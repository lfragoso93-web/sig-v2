"""Refatora tabela transactions para estrutura ticker-based

Revision ID: 006_tx_ticker_based
Revises: 005_portfolio_snapshots
Create Date: 2026-06-18

Estado do banco ANTES desta migration:
  Colunas existentes:
    id, portfolio_id, asset_id (FK assets), transaction_type (enum),
    date, quantity, unit_price, total_cost, fees, broker, notes,
    is_day_trade, created_at, updated_at,
    currency (adicionada pela 002)

Esta migration:
  - Adiciona: ticker, asset_type, operation (enum operationtype), price
  - Migra dados existentes
  - Remove: asset_id, transaction_type, unit_price, total_cost, broker, is_day_trade
  - currency ja existe (002) — nao toca
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '006_tx_ticker_based'
down_revision = '005_portfolio_snapshots'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Cria enum operationtype se nao existir
    conn.execute(text("""
        DO $$ BEGIN
            CREATE TYPE operationtype AS ENUM ('buy', 'sell');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """))

    # 2. Adiciona colunas novas (IF NOT EXISTS para idempotencia)
    conn.execute(text("""
        ALTER TABLE transactions
        ADD COLUMN IF NOT EXISTS ticker VARCHAR(100) NULL;
    """))
    conn.execute(text("""
        ALTER TABLE transactions
        ADD COLUMN IF NOT EXISTS asset_type VARCHAR(30) NULL;
    """))
    conn.execute(text("""
        ALTER TABLE transactions
        ADD COLUMN IF NOT EXISTS price NUMERIC(18, 8) NULL;
    """))
    # operation precisa de tratamento especial por ser enum
    try:
        conn.execute(text("""
            ALTER TABLE transactions
            ADD COLUMN operation operationtype NULL;
        """))
    except Exception:
        pass  # coluna ja existe

    # 3. Migra dados existentes via JOIN com assets
    conn.execute(text("""
        UPDATE transactions t
        SET
            ticker     = COALESCE(a.ticker, 'DESCONHECIDO'),
            asset_type = COALESCE(a.asset_type::text, 'OUTRO'),
            operation  = CASE
                             WHEN t.transaction_type::text IN (
                                 'COMPRA','TRANSFERENCIA_ENTRADA',
                                 'BONIFICACAO','DESDOBRAMENTO'
                             ) THEN 'buy'::operationtype
                             ELSE 'sell'::operationtype
                         END,
            price      = COALESCE(t.unit_price, 0)
        FROM assets a
        WHERE t.asset_id = a.id
          AND t.ticker IS NULL;
    """))

    # 4. Preenche linhas sem asset_id correspondente
    conn.execute(text("""
        UPDATE transactions
        SET
            ticker     = 'DESCONHECIDO',
            asset_type = 'OUTRO',
            operation  = 'buy'::operationtype,
            price      = 0
        WHERE ticker IS NULL;
    """))

    # 5. Torna novas colunas NOT NULL
    conn.execute(text("ALTER TABLE transactions ALTER COLUMN ticker     SET NOT NULL;"))
    conn.execute(text("ALTER TABLE transactions ALTER COLUMN asset_type SET NOT NULL;"))
    conn.execute(text("ALTER TABLE transactions ALTER COLUMN operation  SET NOT NULL;"))
    conn.execute(text("ALTER TABLE transactions ALTER COLUMN price      SET NOT NULL;"))

    # 6. Remove FK de asset_id dinamicamente (nome do constraint pode variar)
    conn.execute(text("""
        DO $$ DECLARE
            r RECORD;
        BEGIN
            FOR r IN (
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'transactions'::regclass
                  AND contype = 'f'
                  AND conname ILIKE '%asset%'
            ) LOOP
                EXECUTE 'ALTER TABLE transactions DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$;
    """))

    # 7. Remove index asset_id se existir
    conn.execute(text("DROP INDEX IF EXISTS ix_transactions_asset_id;"))

    # 8. Remove colunas antigas
    for col in ('asset_id', 'transaction_type', 'unit_price', 'total_cost', 'broker', 'is_day_trade'):
        conn.execute(text(f"ALTER TABLE transactions DROP COLUMN IF EXISTS {col};"))

    # 9. Cria index no ticker
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_transactions_ticker ON transactions (ticker);
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("DROP INDEX IF EXISTS ix_transactions_ticker;"))

    for col, definition in [
        ('asset_id',        'INTEGER NULL'),
        ('transaction_type','VARCHAR(50) NULL'),
        ('unit_price',      'NUMERIC(18,8) NULL'),
        ('total_cost',      'NUMERIC(18,2) NULL'),
        ('broker',          'VARCHAR(100) NULL'),
        ('is_day_trade',    'BOOLEAN NOT NULL DEFAULT false'),
    ]:
        conn.execute(text(
            f"ALTER TABLE transactions ADD COLUMN IF NOT EXISTS {col} {definition};"
        ))

    for col in ('ticker', 'asset_type', 'operation', 'price'):
        conn.execute(text(f"ALTER TABLE transactions DROP COLUMN IF EXISTS {col};"))

    conn.execute(text("DROP TYPE IF EXISTS operationtype;"))
