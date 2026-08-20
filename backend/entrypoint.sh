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

# A contração 20260731_drop_legacy_divs é um artefato operacional protegido da
# Issue #158 e nunca deve ser aplicada implicitamente no startup da aplicação.
# O alvo runtime-safe avança somente até a revisão canônica anterior ao DROP.
RUNTIME_MIGRATION_TARGET="20260729_dividend_identity"
echo "[entrypoint] Executando migrations runtime-safe ate ${RUNTIME_MIGRATION_TARGET}..."
alembic upgrade "${RUNTIME_MIGRATION_TARGET}"

echo "[entrypoint] Criando/atualizando superadmin..."
python -m scripts.create_superadmin

echo "[entrypoint] Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
