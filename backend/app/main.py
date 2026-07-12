import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text, select, func

from app.core.database import engine, AsyncSessionLocal
from app.core.config import settings
from app.core.limiter import limiter
from app.core.scheduler import start_scheduler
from app.core.cache import get_redis
from app.middleware import SecurityHeadersMiddleware
from app.routers import (
    auth, portfolios, transactions, dividends, positions,
    users, proventos, performance, admin,
    assets, sync, fx, goals, irpf,
    analysis, fixed_income, quotes, treasury,
)
from app.routers import debug
from app.routers import prices
from app.routers import class_targets
from app.routers import rentabilidade

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


async def _boot_sequence() -> None:
    """
    Sequência de inicialização executada em background após o app subir.

    Etapa 1 - Seed de ativos B3/cripto.
    Etapa 1b - Seed/atualização do catálogo de Tesouro Direto.
    Etapa 1c - Reconciliação de lançamentos antigos de Tesouro Direto.
    Etapa 1d - Histórico/snapshot de Tesouro Direto.
    Etapa 2 - Backfill histórico de preços.
    Etapa 3 - Backfill/incremental de benchmarks para Renda Fixa.
    """
    await asyncio.sleep(3)

    seed_ok = False
    try:
        from app.models.asset import Asset
        from app.services.asset_seed_service import run_asset_seed

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(func.count()).select_from(Asset))
            asset_count = result.scalar_one() or 0

        if asset_count == 0:
            logger.info("[Boot] Etapa 1: tabela assets vazia — iniciando seed de tickers")
            async with AsyncSessionLocal() as db:
                seed_result = await run_asset_seed(db, run_backfill=False)
            logger.info(
                "[Boot] Etapa 1: seed concluido — %d criados, %d atualizados, %d erros",
                seed_result.created, seed_result.updated, seed_result.errors,
            )
            seed_ok = True
        else:
            logger.info("[Boot] Etapa 1: %d assets no banco — seed ignorado", asset_count)
            seed_ok = True

    except Exception as e:
        logger.error("[Boot] Etapa 1 (seed de ativos) falhou: %s", e)
        seed_ok = False

    try:
        from app.services.treasury_catalog_service import seed_treasury_assets

        logger.info("[Boot] Etapa 1b: atualizando catálogo Tesouro Direto")
        async with AsyncSessionLocal() as db:
            treasury_seed = await seed_treasury_assets(db)
        logger.info(
            "[Boot] Etapa 1b: Tesouro Direto — %d criados, %d atualizados, %d ignorados, %d erros",
            treasury_seed.created,
            treasury_seed.updated,
            treasury_seed.skipped,
            treasury_seed.errors,
        )
    except Exception as e:
        logger.error("[Boot] Etapa 1b (seed Tesouro Direto) falhou: %s", e)

    try:
        from app.services.treasury_reconciliation_service import reconcile_treasury_transactions

        logger.info("[Boot] Etapa 1c: reconciliando lançamentos Tesouro Direto existentes")
        async with AsyncSessionLocal() as db:
            reconciliation = await reconcile_treasury_transactions(db)
        logger.info(
            "[Boot] Etapa 1c: Tesouro Direto reconciliado — %d lidos, %d transações atualizadas, %d assets criados, %d sem match, %d erros",
            reconciliation.scanned,
            reconciliation.updated_transactions,
            reconciliation.created_assets,
            reconciliation.unresolved,
            reconciliation.errors,
        )
    except Exception as e:
        logger.error("[Boot] Etapa 1c (reconciliação Tesouro Direto) falhou: %s", e)

    try:
        from app.services.treasury_price_history_service import (
            import_missing_treasury_price_history,
            update_treasury_latest_prices,
        )

        logger.info("[Boot] Etapa 1d: verificando histórico Tesouro Direto")
        treasury_stats = await import_missing_treasury_price_history()
        logger.info("[Boot] Etapa 1d: histórico Tesouro Direto atualizado: %s", treasury_stats)
        async with AsyncSessionLocal() as db:
            snapshot = await update_treasury_latest_prices(db)
        logger.info("[Boot] Etapa 1d: snapshot Tesouro Direto atualizado: %d títulos", len(snapshot))
    except Exception as e:
        logger.error("[Boot] Etapa 1d (histórico Tesouro Direto) falhou: %s", e)

    if not seed_ok:
        logger.warning("[Boot] Etapa 2 abortada: etapa 1 falhou")
    else:
        try:
            from app.services.price_history_backfill_service import run_initial_backfill
            logger.info("[Boot] Etapa 2: verificando necessidade de backfill de precos")
            await run_initial_backfill()
            logger.info("[Boot] Etapa 2: backfill de precos concluido")
        except Exception as e:
            logger.error("[Boot] Etapa 2 (backfill de precos) falhou: %s", e)

    try:
        from app.services.benchmark_rate_service import import_missing_benchmark_history

        logger.info("[Boot] Etapa 3: verificando benchmarks de renda fixa")
        async with AsyncSessionLocal() as db:
            stats = await import_missing_benchmark_history(db)
        logger.info("[Boot] Etapa 3: benchmarks de renda fixa atualizados: %s", stats)
    except Exception as e:
        logger.error("[Boot] Etapa 3 (benchmarks de renda fixa) falhou: %s", e)

    logger.info("[Boot] sequencia de inicializacao concluida")


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    asyncio.create_task(_boot_sequence())
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
                "detail": _sanitize_provider_text(str(exc)),
                "type": type(exc).__name__,
                "traceback": _sanitize_provider_text(tb),
                "path": str(request.url),
            },
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
app.include_router(quotes.router,          prefix=f"{PREFIX}/quotes",       tags=["quotes"])
app.include_router(prices.router,          prefix=f"{PREFIX}/prices",       tags=["prices"])

app.include_router(sync.router,            prefix=f"{PREFIX}/sync",         tags=["sync"])
app.include_router(irpf.router,            prefix=f"{PREFIX}/irpf",         tags=["irpf"])
app.include_router(analysis.router,        prefix=f"{PREFIX}/analysis",     tags=["analysis"])
app.include_router(fixed_income.router,    prefix=f"{PREFIX}/fixed-income", tags=["fixed_income"])

if settings.APP_DEBUG or __import__('os').getenv("ADMIN_SECRET"):
    app.include_router(debug.router, prefix=f"{PREFIX}/debug", tags=["debug"])


@app.get("/health", tags=["health"])
async def health():
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
    }
    status_code = 200 if overall_ok else 503
    return JSONResponse(content=payload, status_code=status_code)
