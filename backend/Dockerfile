# ---- PostgreSQL 16 client stage ----
# Keep dump/restore binaries on the same major as the PostgreSQL server.
FROM postgres:16-bookworm AS postgres-client

# ---- deps stage ----
FROM python:3.12-slim AS deps

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim AS runtime

ARG APP_COMMIT_SHA=unknown
ENV APP_COMMIT_SHA=$APP_COMMIT_SHA
LABEL org.opencontainers.image.revision=$APP_COMMIT_SHA

WORKDIR /app

# Atualiza todos os pacotes do SO para garantir patches de seguranca
# (inclui libssh2-1t64 >= 1.11.1-1+deb13u1 que corrige CVE-2026-55200 e CVE-2026-7598)
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        postgresql-client \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Sobrescreve os clientes genéricos da distribuição com PostgreSQL 16.
COPY --from=postgres-client /usr/lib/postgresql/16/bin/pg_dump /usr/local/bin/pg_dump
COPY --from=postgres-client /usr/lib/postgresql/16/bin/pg_restore /usr/local/bin/pg_restore
COPY --from=postgres-client /usr/lib/postgresql/16/bin/psql /usr/local/bin/psql

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .

# Normaliza line endings e garante permissao de execucao
RUN sed -i 's/\r//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "/app/entrypoint.sh"]
