from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncConnection

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

# Cada ENUM e criado individualmente com IF NOT EXISTS.
# Precisam rodar fora de bloco transacional (AUTOCOMMIT) pois o PostgreSQL
# nao permite DDL de tipo dentro de transacao quando o tipo ja existe.
_ENUMS: list[str] = [
    "CREATE TYPE IF NOT EXISTS userrole AS ENUM ('user', 'superadmin')",
    "CREATE TYPE IF NOT EXISTS dividendstatus AS ENUM ('RECEBIDO', 'A_RECEBER')",
    "CREATE TYPE IF NOT EXISTS dividendtype AS ENUM ('DIVIDENDO', 'JCP', 'RENDIMENTO', 'AMORTIZACAO', 'BONIFICACAO', 'OUTROS')",
    "CREATE TYPE IF NOT EXISTS assettype AS ENUM ('ACAO', 'FII', 'ETF_NACIONAL', 'TESOURO_DIRETO', 'STOCK', 'ETF_INTERNACIONAL', 'CRIPTO', 'RENDA_FIXA')",
    "CREATE TYPE IF NOT EXISTS assetcurrency AS ENUM ('BRL', 'USD', 'EUR', 'BTC')",
    "CREATE TYPE IF NOT EXISTS corporateeventtype AS ENUM ('DESDOBRAMENTO', 'GRUPAMENTO', 'BONIFICACAO')",
    "CREATE TYPE IF NOT EXISTS corporateeventstatus AS ENUM ('PENDENTE', 'APLICADO', 'IGNORADO')",
    "CREATE TYPE IF NOT EXISTS fixedincometype AS ENUM ('CDB', 'LCI', 'LCA', 'LCI_LCA', 'CRI', 'CRA', 'DEBENTURE', 'POUPANCA', 'OUTROS')",
    "CREATE TYPE IF NOT EXISTS indexertype AS ENUM ('CDI', 'IPCA_PLUS', 'SELIC', 'PREFIXADO', 'IGPM_PLUS')",
    "CREATE TYPE IF NOT EXISTS irpfmarket AS ENUM ('ACOES', 'DAY_TRADE', 'FII', 'ETF', 'CRIPTO', 'RENDA_FIXA', 'STOCKS')",
    "CREATE TYPE IF NOT EXISTS goaltype AS ENUM ('PATRIMONIO_ALVO', 'ALOCACAO', 'DY_MENSAL', 'RENTABILIDADE', 'APORTE_MENSAL')",
    "CREATE TYPE IF NOT EXISTS treasurytype AS ENUM ('Tesouro Selic', 'Tesouro Prefixado', 'Tesouro Prefixado com Juros Semestrais', 'Tesouro IPCA+', 'Tesouro IPCA+ com Juros Semestrais', 'Tesouro IGP-M+ com Juros Semestrais', 'Tesouro Renda+', 'Tesouro Educa+')",
]


async def _create_enums_autocommit() -> None:
    """Cria todos os ENUMs fora de transacao (AUTOCOMMIT) para ser idempotente."""
    # Conecta diretamente com isolation_level=AUTOCOMMIT para que cada
    # CREATE TYPE seja executado fora de bloco transacional.
    async with engine.connect() as conn:
        await conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in _ENUMS:
            await conn.execute(text(stmt))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Garante todos os ENUMs (idempotente, AUTOCOMMIT)
    await _create_enums_autocommit()

    # 2. Cria tabelas que ainda nao existem (checkfirst=True)
    #    Em producao prefira apenas "alembic upgrade head" via entrypoint.
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
