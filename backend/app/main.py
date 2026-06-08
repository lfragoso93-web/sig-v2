from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Routers
from app.routers import auth, users, portfolios, transactions, dividends, performance, fx

app = FastAPI(
    title="SIG v2 - Sistema de Investimentos",
    version="2.0.0",
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

# Registro de routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(portfolios.router)
app.include_router(transactions.router)
app.include_router(dividends.router)
app.include_router(performance.router)
app.include_router(fx.router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
