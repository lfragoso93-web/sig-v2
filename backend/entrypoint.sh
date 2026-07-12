#!/bin/sh
set -e

echo "[entrypoint] Aguardando PostgreSQL..."
until python -c "
import os, asyncio, asyncpg
url = os.environ.get('DATABASE_URL', 'postgresql://sgi:sgi@db:5432/sgi')
asyncio.run(asyncpg.connect(url.replace('postgresql+asyncpg', 'postgresql')))
" 2>/dev/null; do
  sleep 1
done

echo "[entrypoint] Executando migrations ate 022 (pre-drop)..."
alembic upgrade 022

echo "[entrypoint] Migrando dados de treasury_investments -> transactions..."
python -m scripts.migrate_treasury

echo "[entrypoint] Heads Alembic detectadas:"
alembic heads

echo "[entrypoint] Executando migrations restantes em todas as branches (023+)..."
alembic upgrade heads

echo "[entrypoint] Garantindo tabelas opcionais usadas pelo ORM..."
python - <<'PY'
import asyncio
from app.core.database import engine
from app.models.corporate_event import CorporateEvent
from app.models.goal import Goal
from app.models.irpf import IRPFReport

OPTIONAL_TABLES = (
    CorporateEvent.__table__,
    Goal.__table__,
    IRPFReport.__table__,
)

async def main() -> None:
    async with engine.begin() as conn:
        for table in OPTIONAL_TABLES:
            await conn.run_sync(table.create, checkfirst=True)

asyncio.run(main())
PY

echo "[entrypoint] Criando/atualizando superadmin..."
python -m scripts.create_superadmin

echo "[entrypoint] Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
