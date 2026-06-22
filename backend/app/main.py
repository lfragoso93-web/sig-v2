import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.database import engine
from app.core.config import settings
from app.core.scheduler import start_scheduler
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

# ---------------------------------------------------------------------------
# Rate limiter (slowapi)
# Usa Redis se REDIS_URL estiver configurado; fallback para memoria.
# ---------------------------------------------------------------------------
_storage_uri = settings.REDIS_URL if settings.REDIS_URL else "memory://"
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=[],
)


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


# Wrapper com assinatura compativel com add_exception_handler (mypy exige
# Callable[[Request, Exception], Response | Awaitable[Response]]).
def _rate_limit_handler(request: Request, exc: Exception) -> Response:
    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]


# Handler de 429 -- retorna JSON padrao em vez de HTML
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

# Middleware slowapi (necessario para key_func acessar o request)
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
# proventos router ja tem prefix="/portfolios/{portfolio_id}/proventos" internamente
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "debug": settings.APP_DEBUG}
