from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.routers import auth, users, admin, portfolios, transactions, assets, dividends
from app.scheduler import init_scheduler, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_scheduler()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="SIG v2 - Sistema de Investimentos Gerenciado",
    description="API para gestao de carteiras de investimentos multi-usuario",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",       tags=["Auth"])
app.include_router(users.router,        prefix="/api/users",      tags=["Users"])
app.include_router(admin.router,        prefix="/api/admin",      tags=["Admin"])
app.include_router(portfolios.router,   prefix="/api/portfolios", tags=["Portfolios"])
app.include_router(transactions.router, prefix="/api/portfolios", tags=["Transactions"])
app.include_router(dividends.router,    prefix="/api/portfolios", tags=["Dividends"])
app.include_router(assets.router,       prefix="/api/assets",     tags=["Assets"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
