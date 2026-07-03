import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

BRAPI_CHUNK_DELAY = 1.0  # segundos entre chunks BRAPI


def start_scheduler() -> None:
    """
    Registra jobs de cotação, benchmarks e catálogo de Tesouro Direto.
    """

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour="9-18", minute="*/15"),
        id="update_quotes_acoes",
        name="Atualizar cotacoes BRAPI — ACAO",
    )
    async def update_quotes_acoes():
        from app.services.quotes_service import update_all_quotes
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        async with AsyncSessionLocal() as db:
            try:
                await update_all_quotes(db, asset_types=[AssetType.ACAO])
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar ACAO: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour="9-18", minute="*/15"),
        id="update_quotes_fiis",
        name="Atualizar cotacoes BRAPI — FII",
    )
    async def update_quotes_fiis():
        from app.services.quotes_service import update_all_quotes
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        async with AsyncSessionLocal() as db:
            try:
                await update_all_quotes(db, asset_types=[AssetType.FII])
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar FII: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour="9-18", minute="*/15"),
        id="update_quotes_etf_bdr",
        name="Atualizar cotacoes BRAPI — ETF_NACIONAL / BDR",
    )
    async def update_quotes_etf_bdr():
        from app.services.quotes_service import update_all_quotes
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        async with AsyncSessionLocal() as db:
            try:
                await update_all_quotes(
                    db,
                    asset_types=[AssetType.ETF_NACIONAL, AssetType.BDR],
                )
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar ETF_NACIONAL/BDR: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour="9-18", minute="*/15"),
        id="update_quotes_intl",
        name="Atualizar cotacoes — STOCK / ETF_INTERNACIONAL",
    )
    async def update_quotes_intl():
        from app.services.quotes_service import update_all_quotes
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        async with AsyncSessionLocal() as db:
            try:
                await update_all_quotes(
                    db,
                    asset_types=[AssetType.STOCK, AssetType.ETF_INTERNACIONAL],
                )
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar INTL: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour=7, minute=5),
        id="update_treasury_catalog",
        name="Atualizar catálogo BRAPI — Tesouro Direto",
    )
    async def update_treasury_catalog():
        from app.core.database import AsyncSessionLocal
        from app.services.treasury_catalog_service import seed_treasury_assets

        async with AsyncSessionLocal() as db:
            try:
                await seed_treasury_assets(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar catálogo Tesouro Direto: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour=7, minute=10),
        id="update_benchmark_rates",
        name="Atualizar benchmarks SGS/BCB — CDI/SELIC/IPCA/IGPM",
    )
    async def update_benchmark_rates():
        from app.core.database import AsyncSessionLocal
        from app.services.benchmark_rate_service import import_missing_benchmark_history

        async with AsyncSessionLocal() as db:
            try:
                await import_missing_benchmark_history(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar benchmarks SGS/BCB: %s", e)

    scheduler.start()
    logger.info(
        "Scheduler iniciado — cotacoes intraday + Tesouro Direto + benchmarks SGS/BCB diários"
    )
