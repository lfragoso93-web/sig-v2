"""Refatora tabela transactions para estrutura ticker-based

Revision ID: 006_refactor_transactions_ticker_based
Revises: 005_portfolio_snapshots
Create Date: 2026-06-18

Racionale:
  A estrutura original usava asset_id (FK para assets), transaction_type enum,
  unit_price e total_cost. A nova estrutura usa ticker (string livre), asset_type,
  operation enum (buy/sell), price e currency — sem FK para assets, permitindo
  registrar ativos que ainda n\u00e3o est\u00e3o cadastrados na tabela assets.
"""
from alembic import op
import sqlalchemy as sa

revision = '006_refactor_transactions_ticker_based'
down_revision = '005_portfolio_snapshots'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Cria enum operationtype se nao existir
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE operationtype AS ENUM ('buy', 'sell');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # 2. Adiciona colunas novas como nullable primeiro
    op.add_column('transactions', sa.Column('ticker',     sa.String(30),  nullable=True))
    op.add_column('transactions', sa.Column('asset_type', sa.String(30),  nullable=True))
    op.add_column('transactions', sa.Column('operation',  sa.Enum('buy', 'sell', name='operationtype'), nullable=True))
    op.add_column('transactions', sa.Column('price',      sa.Numeric(18, 8), nullable=True))
    op.add_column('transactions', sa.Column('currency',   sa.String(10), nullable=True, server_default='BRL'))

    # 3. Migra dados existentes (se houver) a partir do JOIN com assets
    op.execute("""
        UPDATE transactions t
        SET
            ticker     = COALESCE(a.ticker, 'DESCONHECIDO'),
            asset_type = COALESCE(a.asset_type::text, 'OUTRO'),
            operation  = CASE
                             WHEN t.transaction_type IN ('COMPRA', 'TRANSFERENCIA_ENTRADA', 'BONIFICACAO', 'DESDOBRAMENTO') THEN 'buy'::operationtype
                             ELSE 'sell'::operationtype
                         END,
            price      = COALESCE(t.unit_price, 0),
            currency   = 'BRL'
        FROM assets a
        WHERE t.asset_id = a.id;
    """)

    # 4. Preenche linhas sem asset_id (caso existam)
    op.execute("""
        UPDATE transactions
        SET
            ticker     = 'DESCONHECIDO',
            asset_type = 'OUTRO',
            operation  = 'buy'::operationtype,
            price      = 0,
            currency   = 'BRL'
        WHERE ticker IS NULL;
    """)

    # 5. Torna novas colunas NOT NULL
    op.alter_column('transactions', 'ticker',     nullable=False)
    op.alter_column('transactions', 'asset_type', nullable=False)
    op.alter_column('transactions', 'operation',  nullable=False)
    op.alter_column('transactions', 'price',      nullable=False)
    op.alter_column('transactions', 'currency',   nullable=False, server_default='BRL')

    # 6. Adiciona coluna notes se nao existir (era nullable na 001, mantemos)
    # Ja existe na 001, nada a fazer.

    # 7. Remove colunas antigas
    # Remove FK constraint asset_id antes de dropar a coluna
    op.execute("""
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
    """)

    op.drop_index('ix_transactions_asset_id', table_name='transactions', if_exists=True)
    op.drop_column('transactions', 'asset_id')
    op.drop_column('transactions', 'transaction_type')
    op.drop_column('transactions', 'unit_price')
    op.drop_column('transactions', 'total_cost')
    op.drop_column('transactions', 'broker')
    op.drop_column('transactions', 'is_day_trade')

    # 8. Cria indice no ticker para performance
    op.create_index('ix_transactions_ticker', 'transactions', ['ticker'])


def downgrade() -> None:
    # Revert: recria colunas antigas como nullable, dropa novas
    op.drop_index('ix_transactions_ticker', table_name='transactions')

    op.add_column('transactions', sa.Column('asset_id',        sa.Integer(), nullable=True))
    op.add_column('transactions', sa.Column('transaction_type', sa.String(50), nullable=True))
    op.add_column('transactions', sa.Column('unit_price',      sa.Numeric(18, 8), nullable=True))
    op.add_column('transactions', sa.Column('total_cost',      sa.Numeric(18, 2), nullable=True))
    op.add_column('transactions', sa.Column('broker',          sa.String(100), nullable=True))
    op.add_column('transactions', sa.Column('is_day_trade',    sa.Boolean(), nullable=True, server_default='false'))

    op.drop_column('transactions', 'ticker')
    op.drop_column('transactions', 'asset_type')
    op.drop_column('transactions', 'operation')
    op.drop_column('transactions', 'price')
    op.drop_column('transactions', 'currency')

    op.execute('DROP TYPE IF EXISTS operationtype')
