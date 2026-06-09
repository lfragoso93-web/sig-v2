from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.core.scheduler import start_scheduler
from app.routers import (
    auth, portfolios, transactions, dividends, positions,
    users, proventos, performance, admin,
    assets, sync, fx, goals, irpf,
    analysis, fixed_income, quotes, treasury,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
    ],
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
