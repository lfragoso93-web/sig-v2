import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

BRAPI_CHUNK_DELAY = 1.0


def start_scheduler() -> None:
    """Registra jobs operacionais e de manutenção de dados de mercado."""

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
                await update_all_quotes(db, asset_types=[AssetType.ETF_NACIONAL, AssetType.BDR])
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
                await update_all_quotes(db, asset_types=[AssetType.STOCK, AssetType.ETF_INTERNACIONAL])
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
        CronTrigger(day_of_week="mon-fri", hour=7, minute=8),
        id="update_treasury_history",
        name="Atualizar histórico BRAPI — Tesouro Direto",
    )
    async def update_treasury_history():
        from app.core.database import AsyncSessionLocal
        from app.services.treasury_price_history_service import import_treasury_price_history, update_treasury_latest_prices
        async with AsyncSessionLocal() as db:
            try:
                await import_treasury_price_history(db, only_missing=True)
                await update_treasury_latest_prices(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar histórico Tesouro Direto: %s", e)

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

    @scheduler.scheduled_job(
        CronTrigger(hour=9, minute=0),
        id="sync_daily_proventos_morning",
        name="Sincronizar proventos/eventos BRAPI — renda variável nacional (09:00)",
        max_instances=1,
        coalesce=True,
    )
    @scheduler.scheduled_job(
        CronTrigger(hour=18, minute=10),
        id="sync_daily_proventos_evening",
        name="Sincronizar proventos/eventos BRAPI — renda variável nacional (18:10)",
        max_instances=1,
        coalesce=True,
    )
    async def sync_daily_proventos():
        from app.core.database import AsyncSessionLocal
        from app.services.proventos_daily_sync_service import run_daily_proventos_sync
        async with AsyncSessionLocal() as db:
            try:
                result = await run_daily_proventos_sync(db)
                logger.info("[scheduler] Proventos diários atualizados: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro ao sincronizar proventos diários: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour=20, minute=20),
        id="sync_market_pipeline_held_assets",
        name="Pipeline incremental — ativos em carteira",
        max_instances=1,
        coalesce=True,
    )
    async def sync_market_pipeline_held_assets():
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.services.market_pipeline_batch_service import run_market_pipeline_batch
        async with AsyncSessionLocal() as db:
            try:
                result = await run_market_pipeline_batch(
                    db,
                    asset_types={AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL, AssetType.BDR},
                    only_held=True,
                    concurrency=1,
                    delay=0.5,
                    full=False,
                    sync_prices=True,
                    sync_logo=True,
                    sync_events=True,
                    materialize=True,
                )
                logger.info("[scheduler] Pipeline incremental da carteira atualizado: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro no pipeline incremental da carteira: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour=20, minute=45),
        id="global_asset_price_gap_maintenance",
        name="Auditar e preencher lacunas globais de preços",
        max_instances=1,
        coalesce=True,
    )
    async def global_asset_price_gap_maintenance():
        from app.services.asset_price_global_backfill_service import (
            run_global_asset_price_backfill,
        )
        try:
            result = await run_global_asset_price_backfill()
            logger.info("[scheduler] Cobertura global de preços atualizada: %s", result)
        except Exception as e:
            logger.error("[scheduler] Erro na cobertura global de preços: %s", e)

    @scheduler.scheduled_job(
        CronTrigger(day_of_week="mon-fri", hour=21, minute=0),
        id="portfolio_snapshot_auto_maintenance",
        name="Manutencao automatica de snapshots patrimoniais e TWR",
        max_instances=1,
        coalesce=True,
    )
    async def portfolio_snapshot_auto_maintenance():
        from app.core.database import AsyncSessionLocal
        from app.services.portfolio_snapshot_twr_maintenance_service import (
            maintain_twr_snapshots_for_active_portfolios,
        )
        async with AsyncSessionLocal() as db:
            try:
                result = await maintain_twr_snapshots_for_active_portfolios(db)
                logger.info("[scheduler] Snapshots patrimoniais/TWR atualizados: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro na manutencao de snapshots TWR: %s", e)

    scheduler.start()
    logger.info(
        "Scheduler iniciado — cotações intraday + Tesouro Direto + benchmarks + proventos + pipeline + cobertura global de preços + snapshots TWR"
    )
