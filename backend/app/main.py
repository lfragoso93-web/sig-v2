import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.core.database import engine, AsyncSessionLocal
from app.core.config import settings
from app.core.limiter import limiter
from app.core.scheduler import start_scheduler
from app.core.cache import get_redis
from app.routers import (
    auth, portfolios, transactions, dividends, positions,
    users, proventos, performance, admin,
    assets, sync, fx, goals, irpf,
    analysis, fixed_income, quotes, treasury,
)
from app.routers import debug
from app.routers import prices
from app.routers import class_targets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    await engine.dispose()


app = FastAPI(
    title="SGI v2 API",
    description="Sistema de Gerenciamento de Investimentos",
    version="2.0.0",
    lifespan=lifespan,
)

# Injeta o limiter no state para que @limiter.limit() funcione nos routers
app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url,
        exc,
        tb,
    )
    if settings.APP_DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "traceback": tb,
                "path": str(request.url),
            },
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. Contate o suporte."},
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})
    schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Cole aqui o access_token obtido em POST /api/v1/auth/login",
    }
    schema["security"] = [
        {"OAuth2PasswordBearer": []},
        {"HTTPBearer": []},
    ]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]

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
app.include_router(auth.router,            prefix=f"{PREFIX}/auth",         tags=["auth"])
app.include_router(users.router,           prefix=f"{PREFIX}/users",        tags=["users"])
app.include_router(admin.router,           prefix=f"{PREFIX}/admin",        tags=["admin"])

# Core financeiro
app.include_router(portfolios.router,      prefix=f"{PREFIX}/portfolios",   tags=["portfolios"])
app.include_router(transactions.router,    prefix=f"{PREFIX}/portfolios",   tags=["transactions"])
app.include_router(treasury.router,        prefix=f"{PREFIX}/portfolios",   tags=["treasury"])
app.include_router(positions.router,       prefix=f"{PREFIX}/positions",    tags=["positions"])
app.include_router(dividends.router,       prefix=f"{PREFIX}/portfolios",   tags=["dividends"])
app.include_router(proventos.router,       prefix=f"{PREFIX}",              tags=["proventos"])
app.include_router(performance.router,     prefix=f"{PREFIX}/performance",  tags=["performance"])
app.include_router(class_targets.router,   prefix=f"{PREFIX}/portfolios",   tags=["class-targets"])

# Dados de mercado
app.include_router(assets.router,          prefix=f"{PREFIX}/assets",       tags=["assets"])
app.include_router(fx.router,              prefix=f"{PREFIX}/fx",           tags=["fx"])
app.include_router(quotes.router,          prefix=f"{PREFIX}/quotes",       tags=["quotes"])
app.include_router(prices.router,          prefix=f"{PREFIX}/prices",       tags=["prices"])

# Funcionalidades extras
app.include_router(sync.router,            prefix=f"{PREFIX}/sync",         tags=["sync"])
app.include_router(goals.router,           prefix=f"{PREFIX}/goals",        tags=["goals"])
app.include_router(irpf.router,            prefix=f"{PREFIX}/irpf",         tags=["irpf"])
app.include_router(analysis.router,        prefix=f"{PREFIX}/analysis",     tags=["analysis"])
app.include_router(fixed_income.router,    prefix=f"{PREFIX}/fixed-income", tags=["fixed_income"])

if settings.APP_DEBUG or __import__('os').getenv("ADMIN_SECRET"):
    app.include_router(debug.router, prefix=f"{PREFIX}/debug", tags=["debug"])


@app.get("/health", tags=["health"])
async def health():
    """
    Health check real: verifica conectividade com PostgreSQL e Redis.
    Retorna 200 se ambos ok, 503 se algum falhar.
    """
    checks: dict[str, str] = {}
    overall_ok = True

    # --- PostgreSQL: SELECT 1 ---
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.error("[health] postgres falhou: %s", e)
        checks["postgres"] = "error"
        overall_ok = False

    # --- Redis: ping ---
    try:
        client = await get_redis()
        if client:
            await client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
            # Redis e opcional — nao derruba o health
    except Exception as e:
        logger.warning("[health] redis ping falhou: %s", e)
        checks["redis"] = "error"
        # Redis e opcional — nao derruba o health

    payload = {
        "status": "ok" if overall_ok else "degraded",
        "version": "2.0.0",
        "debug": settings.APP_DEBUG,
        "checks": checks,
    }
    status_code = 200 if overall_ok else 503
    return JSONResponse(content=payload, status_code=status_code)
