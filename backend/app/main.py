import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.core.cache import get_redis
from app.core.config import settings
from app.core.database import AsyncSessionLocal, engine
from app.core.limiter import limiter
from app.core.scheduler import start_scheduler
from app.middleware import SecurityHeadersMiddleware
from app.routers import (
    admin,
    assets,
    auth,
    class_targets,
    dividends,
    fx,
    goals,
    irpf,
    performance,
    portfolios,
    positions,
    prices,
    proventos,
    rentabilidade,
    transactions,
    treasury,
    users,
)
from app.routers.admin_bootstrap import router as admin_bootstrap_router

logger = logging.getLogger(__name__)

_PROVIDER_TERMS = (
    "brapi",
    "yfinance",
    "yahoo finance",
    "alpha vantage",
    "tesouro transparente",
)
_PUBLIC_MARKET_DATA_SOURCE = "market_data_provider"


def _sanitize_provider_text(value: str) -> str:
    sanitized = value
    for term in _PROVIDER_TERMS:
        sanitized = sanitized.replace(term, _PUBLIC_MARKET_DATA_SOURCE)
        sanitized = sanitized.replace(term.upper(), _PUBLIC_MARKET_DATA_SOURCE)
        sanitized = sanitized.replace(term.title(), _PUBLIC_MARKET_DATA_SOURCE)
    return sanitized


def _sanitize_public_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sanitize_public_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize_public_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_provider_text(value)
    return value


async def _run_startup_bootstrap() -> None:
    from app.services.system_bootstrap_service import run_system_bootstrap

    report = await run_system_bootstrap(startup_delay_seconds=3.0)
    if report.ok:
        logger.info("[Bootstrap] %s concluído: %s", report.schema_version, report.to_dict())
    else:
        logger.error("[Bootstrap] %s incompleto: %s", report.schema_version, report.to_dict())


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.system_readiness_service import mark_bootstrap_disabled

    start_scheduler()
    if settings.ENABLE_BOOT_MARKET_SYNC:
        asyncio.create_task(_run_startup_bootstrap())
    else:
        mark_bootstrap_disabled(
            detail="bootstrap automático desabilitado (ENABLE_BOOT_MARKET_SYNC=false)"
        )
        logger.info(
            "[Bootstrap] bootstrap automático desabilitado "
            "(ENABLE_BOOT_MARKET_SYNC=false)"
        )
    yield
    await engine.dispose()


app = FastAPI(
    title="SGI v2 API",
    description="Sistema de Gerenciamento de Investimentos",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno no servidor. Contate o suporte."},
    )


def custom_openapi() -> dict[str, Any]:
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
    sanitized_schema = _sanitize_public_payload(schema)
    if not isinstance(sanitized_schema, dict):
        raise TypeError("OpenAPI sanitizado deve ser um dicionario")
    app.openapi_schema = sanitized_schema
    return sanitized_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(SecurityHeadersMiddleware)

PREFIX = "/api/v1"

app.include_router(auth.router,            prefix=f"{PREFIX}/auth",         tags=["auth"])
app.include_router(users.router,           prefix=f"{PREFIX}/users",        tags=["users"])
app.include_router(admin.router,           prefix=f"{PREFIX}/admin",        tags=["admin"])
app.include_router(admin_bootstrap_router, prefix=f"{PREFIX}/admin",        tags=["admin-bootstrap"])

app.include_router(portfolios.router,      prefix=f"{PREFIX}/portfolios",   tags=["portfolios"])
app.include_router(transactions.router,    prefix=f"{PREFIX}/portfolios",   tags=["transactions"])
app.include_router(treasury.router,        prefix=f"{PREFIX}/portfolios",   tags=["treasury"])
app.include_router(positions.router,       prefix=f"{PREFIX}/positions",    tags=["positions"])
app.include_router(dividends.router,       prefix=f"{PREFIX}/portfolios",   tags=["dividends"])
app.include_router(proventos.router,       prefix=f"{PREFIX}",              tags=["proventos"])
app.include_router(performance.router,     prefix=f"{PREFIX}/performance",  tags=["performance"])
app.include_router(rentabilidade.router,   prefix=f"{PREFIX}/portfolios",   tags=["rentabilidade"])
app.include_router(class_targets.router,   prefix=f"{PREFIX}/portfolios",   tags=["class-targets"])
app.include_router(goals.router,           prefix=f"{PREFIX}/portfolios",   tags=["goals"])

app.include_router(assets.router,          prefix=f"{PREFIX}/assets",       tags=["assets"])
app.include_router(fx.router,              prefix=f"{PREFIX}/fx",           tags=["fx"])
app.include_router(prices.router,          prefix=f"{PREFIX}/prices",       tags=["prices"])

app.include_router(irpf.router,            prefix=f"{PREFIX}/irpf",         tags=["irpf"])


@app.get("/health", tags=["health"])
async def health():
    from app.services.system_readiness_service import get_bootstrap_readiness

    checks: dict[str, str] = {}
    overall_ok = True

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        logger.error("[health] postgres falhou: %s", e)
        checks["postgres"] = "error"
        overall_ok = False

    try:
        client = await get_redis()
        if client:
            await client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as e:
        logger.warning("[health] redis ping falhou: %s", e)
        checks["redis"] = "error"

    payload = {
        "status": "ok" if overall_ok else "degraded",
        "version": "2.0.0",
        "debug": settings.APP_DEBUG,
        "checks": checks,
        "bootstrap": get_bootstrap_readiness().to_dict(),
    }
    status_code = 200 if overall_ok else 503
    return JSONResponse(content=payload, status_code=status_code)


@app.get("/ready", tags=["health"])
async def ready():
    """Indica se o ambiente está certificado para receber dados reais."""
    from app.services.system_readiness_service import get_bootstrap_readiness

    readiness = get_bootstrap_readiness()
    payload = readiness.to_dict()
    status_code = 200 if readiness.ready_for_real_data else 503
    return JSONResponse(content=payload, status_code=status_code)
