#!/bin/sh
set -e

echo "[entrypoint] Aguardando PostgreSQL..."
until python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))" 2>/dev/null; do
  sleep 1
done

echo "[entrypoint] Executando migrations..."
alembic upgrade head

echo "[entrypoint] Iniciando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
