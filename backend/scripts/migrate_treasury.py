"""
migrate_treasury.py

Script idempotente que migra dados de treasury_investments -> transactions.

Executado automaticamente pelo entrypoint.sh entre:
  alembic upgrade 022  (estado anterior ao drop)
  alembic upgrade head (roda a 023 que dropa a tabela)

Se a tabela treasury_investments nao existir (deploy posterior),
o script simplesmente encerra sem fazer nada.
"""
import asyncio
import os
import logging

import asyncpg

logging.basicConfig(level=logging.INFO, format="[migrate_treasury] %(message)s")
log = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://sgi:sgi@db:5432/sgi")
# asyncpg usa postgresql://, nao postgresql+asyncpg://
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
    WHERE asset_type = 'tesouro_direto'
      AND notes LIKE 'Migrado de treasury_investments%';
"""

MIGRATE_SQL = """
    INSERT INTO transactions (
        portfolio_id,
        ticker,
        asset_type,
        operation,
        quantity,
        price,
        fees,
        date,
        currency,
        notes
    )
    SELECT
        ti.portfolio_id,
        ti.brapi_name,
        'tesouro_direto',
        'buy',
        ti.quantity,
        ti.purchase_price,
        0.0,
        ti.date_purchase,
        'BRL',
        CONCAT(
            'Migrado de treasury_investments | ',
            'Tipo: ', COALESCE(ti.treasury_type::text, 'N/A'), ' | ',
            'Taxa na compra: ', COALESCE(ti.rate_at_purchase::text, 'N/A'), '%'
        )
    FROM treasury_investments ti
    ON CONFLICT DO NOTHING
    RETURNING id;
"""


async def run() -> None:
    conn = await asyncpg.connect(DB_URL)
    try:
        # 1. Verifica se a tabela ainda existe
        table_exists = await conn.fetchval(CHECK_TABLE_SQL)
        if not table_exists:
            log.info("Tabela treasury_investments nao existe — nada a migrar.")
            return

        # 2. Verifica se ja foi migrado anteriormente (idempotencia)
        already = await conn.fetchval(CHECK_ALREADY_MIGRATED_SQL)
        if already and already > 0:
            log.info(
                f"{already} transacoes ja foram migradas anteriormente — pulando."
            )
            return

        # 3. Conta quantos registros serao migrados
        total = await conn.fetchval("SELECT COUNT(*) FROM treasury_investments;")
        log.info(f"Iniciando migracao de {total} registro(s) de treasury_investments...")

        # 4. Executa a migracao dentro de uma transacao
        async with conn.transaction():
            rows = await conn.fetch(MIGRATE_SQL)
            log.info(f"Migracao concluida: {len(rows)} transacao(oes) inserida(s).")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
