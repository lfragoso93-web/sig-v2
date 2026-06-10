#!/bin/sh
set -e

echo "[entrypoint] Aguardando PostgreSQL..."
# Usa a DATABASE_URL sincrona (psycopg2) para o health-check de boot
# A variavel ASYNC_DATABASE_URL nao e suportada pelo asyncpg.connect() diretamente aqui
until python -c "
import os, asyncio, asyncpg
url = os.environ.get('DATABASE_URL', 'postgresql://sgi:sgi@db:5432/sgi')
# asyncpg espera formato postgresql:// (sem +asyncpg)
asyncio.run(asyncpg.connect(url.replace('postgresql+asyncpg', 'postgresql')))
" 2>/dev/null; do
  sleep 1
done

echo "[entrypoint] Executando migrations..."
alembic upgrade head

echo "[entrypoint] Iniciando servidor..."
# --workers 1: evita que o scheduler APScheduler dispare tarefas em duplicata.
# Para escalar horizontalmente use um worker dedicado de scheduler separado.
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
