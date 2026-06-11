from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import asyncpg.exceptions

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

# Enums gerenciados pelo FastAPI no startup.
# treasurytype foi removido: o novo modelo de Tesouro Direto nao usa enum.
_ENUMS: list[tuple] = [
    ("userrole",           "'user'", "'superadmin'"),
    ("dividendstatus",     "'RECEBIDO'", "'A_RECEBER'"),
    ("dividendtype",       "'DIVIDENDO'", "'JCP'", "'RENDIMENTO'", "'AMORTIZACAO'", "'BONIFICACAO'", "'OUTROS'"),
    ("assettype",          "'ACAO'", "'FII'", "'ETF_NACIONAL'", "'TESOURO_DIRETO'", "'STOCK'", "'ETF_INTERNACIONAL'", "'CRIPTO'", "'RENDA_FIXA'"),
    ("assetcurrency",      "'BRL'", "'USD'", "'EUR'", "'BTC'"),
    ("corporateeventtype", "'DESDOBRAMENTO'", "'GRUPAMENTO'", "'BONIFICACAO'"),
    ("corporateeventstatus", "'PENDENTE'", "'APLICADO'", "'IGNORADO'"),
    ("fixedincometype",    "'CDB'", "'LCI'", "'LCA'", "'LCI_LCA'", "'CRI'", "'CRA'", "'DEBENTURE'", "'POUPANCA'", "'OUTROS'"),
    ("indexertype",        "'CDI'", "'IPCA_PLUS'", "'SELIC'", "'PREFIXADO'", "'IGPM_PLUS'"),
    ("irpfmarket",         "'ACOES'", "'DAY_TRADE'", "'FII'", "'ETF'", "'CRIPTO'", "'RENDA_FIXA'", "'STOCKS'"),
    ("goaltype",           "'PATRIMONIO_ALVO'", "'ALOCACAO'", "'DY_MENSAL'", "'RENTABILIDADE'", "'APORTE_MENSAL'"),
]


async def _create_enums_raw() -> None:
    dsn = settings.ASYNC_DATABASE_URL.replace("postgresql+asyncpg", "postgresql")
    conn = await asyncpg.connect(dsn)
    try:
        for enum_def in _ENUMS:
            type_name = enum_def[0]
            values = ", ".join(enum_def[1:])
            # DO NOTHING e a captura de excecao garantem idempotencia
            sql = f"DO $$ BEGIN CREATE TYPE {type_name} AS ENUM ({values}); EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
            await conn.execute(sql)
    finally:
        await conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _create_enums_raw()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
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
app.include_router(transactions.router, prefix=f"{PREFIX}/portfolios",  tags=["transactions"])
app.include_router(treasury.router,     prefix=f"{PREFIX}/portfolios",  tags=["treasury"])
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

import os
if os.getenv("ADMIN_SECRET"):
    app.include_router(debug.router, prefix=f"{PREFIX}/debug", tags=["debug"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
