"""
migrate_treasury.py

Script idempotente que migra dados de treasury_investments -> transactions.

Colunas reais de transactions (conforme model transaction.py):
  id, portfolio_id, asset_id, transaction_type, date,
  quantity, unit_price, total_cost, fees, broker, notes,
  is_day_trade, created_at, updated_at

Este script:
  1. Verifica se treasury_investments ainda existe
  2. Para cada linha, resolve o asset_id via tabela assets
     (cria o asset como TESOURO_DIRETO se nao existir)
  3. Insere em transactions com transaction_type = COMPRA
  4. E idempotente: detecta registros ja migrados e pula
"""
import asyncio
import os
import logging

import asyncpg

logging.basicConfig(level=logging.INFO, format="[migrate_treasury] %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sgi:sgi@db:5432/sgi")
DB_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

CHECK_TABLE_SQL = """
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name   = 'treasury_investments'
    );
"""

CHECK_ALREADY_MIGRATED_SQL = """
    SELECT COUNT(*) FROM transactions
    WHERE notes LIKE 'Migrado de treasury_investments%';
"""

FETCH_TREASURY_SQL = """
    SELECT
        id,
        portfolio_id,
        brapi_name,
        treasury_type,
        date_purchase,
        date_maturity,
        quantity,
        purchase_price,
        invested_amount,
        rate_at_purchase,
        is_active
    FROM treasury_investments
    ORDER BY id;
"""

FIND_ASSET_SQL = """
    SELECT id FROM assets
    WHERE ticker = $1 AND asset_type = 'TESOURO_DIRETO'
    LIMIT 1;
"""

CREATE_ASSET_SQL = """
    INSERT INTO assets (ticker, name, asset_type, currency)
    VALUES ($1, $2, 'TESOURO_DIRETO', 'BRL')
    ON CONFLICT (ticker, asset_type) DO UPDATE SET name = EXCLUDED.name
    RETURNING id;
"""

INSERT_TRANSACTION_SQL = """
    INSERT INTO transactions (
        portfolio_id,
        asset_id,
        transaction_type,
        date,
        quantity,
        unit_price,
        total_cost,
        fees,
        broker,
        notes,
        is_day_trade
    ) VALUES (
        $1, $2, 'COMPRA', $3, $4, $5, $6, 0.0, NULL, $7, false
    );
"""


async def run() -> None:
    conn = await asyncpg.connect(DB_URL)
    try:
        # 1. Verifica se a tabela ainda existe
        table_exists = await conn.fetchval(CHECK_TABLE_SQL)
        if not table_exists:
            log.info("Tabela treasury_investments nao existe — nada a migrar.")
            return

        # 2. Idempotencia: ja foi migrado antes?
        already = await conn.fetchval(CHECK_ALREADY_MIGRATED_SQL)
        if already and already > 0:
            log.info(f"{already} transacoes ja migradas anteriormente — pulando.")
            return

        rows = await conn.fetch(FETCH_TREASURY_SQL)
        log.info(f"Iniciando migracao de {len(rows)} registro(s)...")

        inserted = 0
        async with conn.transaction():
            for row in rows:
                brapi_name = row["brapi_name"]
                ticker = brapi_name.upper().replace(" ", "_")[:30]

                # 3. Resolve asset_id (cria se necessario)
                asset_id = await conn.fetchval(FIND_ASSET_SQL, ticker)
                if not asset_id:
                    asset_id = await conn.fetchval(
                        CREATE_ASSET_SQL, ticker, brapi_name
                    )
                    log.info(f"  Asset criado: {ticker} (id={asset_id})")

                # 4. Monta notes com metadados do titulo
                notes = (
                    f"Migrado de treasury_investments | "
                    f"Tipo: {row['treasury_type'] or 'N/A'} | "
                    f"Taxa na compra: {row['rate_at_purchase'] or 'N/A'}% | "
                    f"Vencimento: {row['date_maturity'] or 'N/A'}"
                )

                await conn.execute(
                    INSERT_TRANSACTION_SQL,
                    row["portfolio_id"],
                    asset_id,
                    row["date_purchase"],
                    float(row["quantity"]),
                    float(row["purchase_price"]),
                    float(row["invested_amount"]),
                    notes,
                )
                inserted += 1

        log.info(f"Migracao concluida: {inserted} transacao(oes) inserida(s).")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
