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

# O runtime não usa `upgrade heads`: migrations destrutivas/operacionais podem
# existir no grafo e não devem ser aplicadas apenas por estarem versionadas.
# O alvo abaixo espelha o head canônico efetivamente validado no ambiente.
RUNTIME_MIGRATION_TARGET="20260820_dividend_occurrence"
echo "[entrypoint] Executando migrations runtime-safe ate ${RUNTIME_MIGRATION_TARGET}..."
alembic upgrade "${RUNTIME_MIGRATION_TARGET}"

echo "[entrypoint] Criando/atualizando superadmin..."
python -m scripts.create_superadmin

echo "[entrypoint] Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
