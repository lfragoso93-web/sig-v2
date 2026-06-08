from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from app.core.config import settings
from app.core.database import engine, Base
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.routers import (
    auth,
    users,
    portfolios,
    transactions,
    assets,
    quotes,
    dividends,
    treasury,
    fixed_income,
    irpf,
    goals,
    analysis,
)
from app.routers import admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação."""
    logger.info("🚀 SGI v2 iniciando...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    logger.info("✅ SGI v2 pronto")
    yield
    shutdown_scheduler()
    await engine.dispose()
    logger.info("👋 SGI v2 encerrado")


app = FastAPI(
    title="SGI v2 — Sistema de Gestão de Investimentos",
    description="API para gerenciamento de carteiras de investimentos com IA",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers públicos / autenticados
app.include_router(auth.router,         prefix="/api/auth",         tags=["Auth"])
app.include_router(users.router,        prefix="/api/users",        tags=["Users"])
app.include_router(portfolios.router,   prefix="/api/portfolios",   tags=["Portfolios"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(assets.router,       prefix="/api/assets",       tags=["Assets"])
app.include_router(quotes.router,       prefix="/api/quotes",       tags=["Quotes"])
app.include_router(dividends.router,    prefix="/api/dividends",    tags=["Dividends"])
app.include_router(treasury.router,     prefix="/api/treasury",     tags=["Treasury"])
app.include_router(fixed_income.router, prefix="/api/fixed-income", tags=["Fixed Income"])
app.include_router(irpf.router,         prefix="/api/irpf",         tags=["IRPF"])
app.include_router(goals.router,        prefix="/api/goals",        tags=["Goals"])
app.include_router(analysis.router,     prefix="/api/analysis",     tags=["Analysis"])

# Router SuperAdmin
app.include_router(admin.router,        prefix="/api/admin",        tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "2.0.0", "system": "SGI"}


@app.get("/api/public/config", tags=["Public"])
async def public_config(
    db=None,
):
    """Endpoint público — retorna configs is_public=true (nome do app, tagline, etc.)."""
    from app.core.database import AsyncSessionLocal
    from app.services.config_service import get_all_configs
    async with AsyncSessionLocal() as session:
        configs = await get_all_configs(session, public_only=True)
        return {c.key: c.value for c in configs}
