from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.database import Base, engine
from app.core.config import settings
from app.core.scheduler import start_scheduler
from app.routers import (
    auth, portfolios, transactions, dividends, positions,
    users, proventos, performance, admin,
    assets, sync, fx, goals, irpf,
    analysis, fixed_income, quotes, treasury,
)
from app.routers import debug

# SQL que cria todos os ENUMs do projeto de forma idempotente.
# Deve ser executado ANTES de qualquer create_table / alembic upgrade.
_CREATE_ENUMS_SQL = """
DO $$
BEGIN
    -- user.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
        CREATE TYPE userrole AS ENUM ('user', 'superadmin');
    END IF;

    -- dividend.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dividendstatus') THEN
        CREATE TYPE dividendstatus AS ENUM ('recebido', 'a_receber');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'dividendtype') THEN
        CREATE TYPE dividendtype AS ENUM (
            'dividendo', 'jcp', 'rendimento', 'amortizacao', 'bonificacao', 'outros'
        );
    END IF;

    -- asset.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assettype') THEN
        CREATE TYPE assettype AS ENUM (
            'ACAO', 'FII', 'ETF_NACIONAL', 'TESOURO_DIRETO',
            'STOCK', 'ETF_INTERNACIONAL', 'CRIPTO', 'RENDA_FIXA'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'assetcurrency') THEN
        CREATE TYPE assetcurrency AS ENUM ('BRL', 'USD', 'EUR', 'BTC');
    END IF;

    -- corporate_event.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'corporateeventtype') THEN
        CREATE TYPE corporateeventtype AS ENUM ('DESDOBRAMENTO', 'GRUPAMENTO', 'BONIFICACAO');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'corporateeventstatus') THEN
        CREATE TYPE corporateeventstatus AS ENUM ('PENDENTE', 'APLICADO', 'IGNORADO');
    END IF;

    -- fixed_income.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fixedincometype') THEN
        CREATE TYPE fixedincometype AS ENUM (
            'CDB', 'LCI', 'LCA', 'LCI_LCA', 'CRI', 'CRA',
            'DEBENTURE', 'POUPANCA', 'OUTROS'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'indexertype') THEN
        CREATE TYPE indexertype AS ENUM (
            'CDI', 'IPCA_PLUS', 'SELIC', 'PREFIXADO', 'IGPM_PLUS'
        );
    END IF;

    -- irpf.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'irpfmarket') THEN
        CREATE TYPE irpfmarket AS ENUM (
            'ACOES', 'DAY_TRADE', 'FII', 'ETF', 'CRIPTO', 'RENDA_FIXA', 'STOCKS'
        );
    END IF;

    -- goal.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'goaltype') THEN
        CREATE TYPE goaltype AS ENUM (
            'PATRIMONIO_ALVO', 'ALOCACAO', 'DY_MENSAL', 'RENTABILIDADE', 'APORTE_MENSAL'
        );
    END IF;

    -- treasury.py
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'treasurytype') THEN
        CREATE TYPE treasurytype AS ENUM (
            'Tesouro Selic', 'Tesouro Prefixado',
            'Tesouro Prefixado com Juros Semestrais',
            'Tesouro IPCA+', 'Tesouro IPCA+ com Juros Semestrais',
            'Tesouro IGP-M+ com Juros Semestrais',
            'Tesouro Renda+', 'Tesouro Educa+'
        );
    END IF;
END$$;
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Garante que todos os ENUMs existem (idempotente)
    async with engine.begin() as conn:
        await conn.execute(text(_CREATE_ENUMS_SQL))

    # 2. Cria tabelas apenas se NAO existirem (sem tentar recriar ENUMs)
    #    Em producao prefira rodar apenas "alembic upgrade head" via entrypoint.
    #    Este bloco e um safety-net para dev/primeiro boot sem migrations aplicadas.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    # 3. Inicia o scheduler (apenas 1 worker deve rodar — ver entrypoint.sh)
    start_scheduler()
    yield
    await engine.dispose()


app = FastAPI(
    title="SGI v2 API",
    description="Sistema de Gerenciamento de Investimentos",
    version="2.0.0",
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"

# Auth & Users
app.include_router(auth.router,         prefix=f"{PREFIX}/auth",        tags=["auth"])
app.include_router(users.router,        prefix=f"{PREFIX}/users",       tags=["users"])
app.include_router(admin.router,        prefix=f"{PREFIX}/admin",       tags=["admin"])

# Core financeiro
app.include_router(portfolios.router,   prefix=f"{PREFIX}/portfolios",  tags=["portfolios"])
app.include_router(transactions.router, prefix=f"{PREFIX}/transactions", tags=["transactions"])
app.include_router(positions.router,    prefix=f"{PREFIX}/positions",   tags=["positions"])
app.include_router(dividends.router,    prefix=f"{PREFIX}/dividends",   tags=["dividends"])
app.include_router(proventos.router,    prefix=f"{PREFIX}/proventos",   tags=["proventos"])
app.include_router(performance.router,  prefix=f"{PREFIX}/performance", tags=["performance"])

# Dados de mercado
app.include_router(assets.router,       prefix=f"{PREFIX}/assets",      tags=["assets"])
app.include_router(fx.router,           prefix=f"{PREFIX}/fx",          tags=["fx"])
app.include_router(quotes.router,       prefix=f"{PREFIX}/quotes",      tags=["quotes"])

# Funcionalidades extras
app.include_router(sync.router,         prefix=f"{PREFIX}/sync",        tags=["sync"])
app.include_router(goals.router,        prefix=f"{PREFIX}/goals",       tags=["goals"])
app.include_router(irpf.router,         prefix=f"{PREFIX}/irpf",        tags=["irpf"])
app.include_router(analysis.router,     prefix=f"{PREFIX}/analysis",    tags=["analysis"])
app.include_router(fixed_income.router, prefix=f"{PREFIX}/fixed-income", tags=["fixed_income"])
app.include_router(treasury.router,     prefix=f"{PREFIX}/treasury",    tags=["treasury"])

# Debug temporario — ativo apenas se ADMIN_SECRET estiver definido
import os
if os.getenv("ADMIN_SECRET"):
    app.include_router(debug.router, prefix=f"{PREFIX}/debug", tags=["debug"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
