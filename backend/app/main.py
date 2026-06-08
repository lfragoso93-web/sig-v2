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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown da aplicação."""
    logger.info("🚀 SIG v2 iniciando...")
    # Cria tabelas (Alembic cuida das migrations em produção)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Inicia o scheduler de cotações
    start_scheduler()
    logger.info("✅ SIG v2 pronto")
    yield
    shutdown_scheduler()
    await engine.dispose()
    logger.info("👋 SIG v2 encerrado")


app = FastAPI(
    title="SIG v2 — Sistema de Investimentos Gerenciado",
    description="API para gerenciamento de carteiras de investimentos",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(assets.router, prefix="/api/assets", tags=["Assets"])
app.include_router(quotes.router, prefix="/api/quotes", tags=["Quotes"])
app.include_router(dividends.router, prefix="/api/dividends", tags=["Dividends"])
app.include_router(treasury.router, prefix="/api/treasury", tags=["Treasury"])
app.include_router(fixed_income.router, prefix="/api/fixed-income", tags=["Fixed Income"])
app.include_router(irpf.router, prefix="/api/irpf", tags=["IRPF"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
