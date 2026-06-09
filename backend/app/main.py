from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.database import Base, engine, AsyncSessionLocal
from app.core.scheduler import start_scheduler
from app.routers import auth, portfolios, transactions, dividends, positions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cria tabelas usando conexao assincrona (checkfirst=True evita erro em ENUMs ja existentes)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    start_scheduler()
    yield

    # Encerra o engine ao desligar
    await engine.dispose()


app = FastAPI(
    title="SGI v2 API",
    description="Sistema de Gerenciamento de Investimentos",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:80", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/v1")
app.include_router(portfolios.router,   prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(dividends.router,    prefix="/api/v1")
app.include_router(positions.router,    prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
