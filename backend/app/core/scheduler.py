import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

SCHEDULER_TIMEZONE = "America/Sao_Paulo"
scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)
BRAPI_CHUNK_DELAY = 1.0
HELD_MARKET_PIPELINE_EVENT_OPTIONS = {
    "sync_events": False,
    "materialize": False,
}
PROVENTOS_SYNC_ONLY_HELD = False


def _cron_trigger(**kwargs) -> CronTrigger:
    """Cria gatilhos sempre no fuso operacional do sistema."""
    return CronTrigger(timezone=SCHEDULER_TIMEZONE, **kwargs)


def _intraday_quote_triggers() -> tuple[CronTrigger, CronTrigger]:
    """Retorna a cadência de 90 minutos entre 09:00 e 18:00 em dias úteis."""
    return (
        _cron_trigger(day_of_week="mon-fri", hour="9,12,15,18", minute=0),
        _cron_trigger(day_of_week="mon-fri", hour="10,13,16", minute=30),
    )


def start_scheduler() -> None:
    """Registra jobs operacionais e de manutenção de dados de mercado."""

    intraday_full_hour, intraday_half_hour = _intraday_quote_triggers()

    @scheduler.scheduled_job(
        intraday_full_hour,
        id="update_quotes_intraday_full_hour",
        name="Atualizar cotações intradiárias — lote completo (hora cheia)",
        max_instances=1,
        coalesce=True,
    )
    @scheduler.scheduled_job(
        intraday_half_hour,
        id="update_quotes_intraday_half_hour",
        name="Atualizar cotações intradiárias — lote completo (meia hora)",
        max_instances=1,
        coalesce=True,
    )
    async def update_quotes_intraday():
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.services.quote_cache_invalidation_service import refresh_quotes_and_invalidate

        asset_types = [
            AssetType.ACAO,
            AssetType.FII,
            AssetType.ETF_NACIONAL,
            AssetType.BDR,
            AssetType.STOCK,
            AssetType.ETF_INTERNACIONAL,
            AssetType.CRIPTO,
        ]
        async with AsyncSessionLocal() as db:
            try:
                updated, invalidated = await refresh_quotes_and_invalidate(db, asset_types)
                logger.info(
                    "[scheduler] Intraday: %s preços, %s carteiras invalidadas",
                    updated,
                    invalidated,
                )
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar cotações intradiárias: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=7, minute=5), id="update_treasury_catalog", name="Atualizar catálogo BRAPI — Tesouro Direto")
    async def update_treasury_catalog():
        from app.core.database import AsyncSessionLocal
        from app.services.treasury_catalog_service import seed_treasury_assets
        async with AsyncSessionLocal() as db:
            try:
                await seed_treasury_assets(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar catálogo Tesouro Direto: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=7, minute=8), id="update_treasury_history", name="Atualizar histórico BRAPI — Tesouro Direto")
    async def update_treasury_history():
        from app.core.database import AsyncSessionLocal
        from app.services.treasury_price_history_service import import_treasury_price_history, update_treasury_latest_prices
        async with AsyncSessionLocal() as db:
            try:
                await import_treasury_price_history(db, only_missing=True)
                await update_treasury_latest_prices(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar histórico Tesouro Direto: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=7, minute=10), id="update_benchmark_rates", name="Atualizar benchmarks SGS/BCB — CDI/SELIC/IPCA/IGPM")
    async def update_benchmark_rates():
        from app.core.database import AsyncSessionLocal
        from app.services.benchmark_rate_service import import_missing_benchmark_history
        async with AsyncSessionLocal() as db:
            try:
                await import_missing_benchmark_history(db)
            except Exception as e:
                logger.error("[scheduler] Erro ao atualizar benchmarks SGS/BCB: %s", e)

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=18, minute=10),
        id="sync_daily_proventos_evening",
        name="Sincronizar proventos/eventos — ativos mantidos (18:10)",
        max_instances=1,
        coalesce=True,
    )
    async def sync_daily_proventos():
        from app.core.database import AsyncSessionLocal
        from app.services.proventos_daily_sync_service import run_daily_proventos_sync
        async with AsyncSessionLocal() as db:
            try:
                result = await run_daily_proventos_sync(
                    db,
                    only_held=PROVENTOS_SYNC_ONLY_HELD,
                )
                logger.info("[scheduler] Proventos diários atualizados: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro ao sincronizar proventos diários: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=20, minute=20), id="sync_market_pipeline_held_assets", name="Pipeline incremental — ativos em carteira", max_instances=1, coalesce=True)
    async def sync_market_pipeline_held_assets():
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.services.market_pipeline_batch_service import run_market_pipeline_batch
        async with AsyncSessionLocal() as db:
            try:
                result = await run_market_pipeline_batch(
                    db,
                    asset_types={
                        AssetType.ACAO,
                        AssetType.FII,
                        AssetType.ETF_NACIONAL,
                        AssetType.BDR,
                    },
                    only_held=True,
                    concurrency=1,
                    delay=0.5,
                    full=False,
                    sync_prices=True,
                    sync_logo=True,
                    **HELD_MARKET_PIPELINE_EVENT_OPTIONS,
                )
                logger.info("[scheduler] Pipeline incremental da carteira atualizado: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro no pipeline incremental da carteira: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=20, minute=45), id="global_asset_price_gap_maintenance", name="Auditar e preencher lacunas globais de preços", max_instances=1, coalesce=True)
    async def global_asset_price_gap_maintenance():
        from app.services.asset_price_global_backfill_service import run_global_asset_price_backfill
        try:
            result = await run_global_asset_price_backfill()
            logger.info("[scheduler] Cobertura global de preços atualizada: %s", result)
        except Exception as e:
            logger.error("[scheduler] Erro na cobertura global de preços: %s", e)

    @scheduler.scheduled_job(_cron_trigger(day_of_week="mon-fri", hour=21, minute=0), id="portfolio_snapshot_auto_maintenance", name="Manutencao automatica de snapshots patrimoniais e TWR", max_instances=1, coalesce=True)
    async def portfolio_snapshot_auto_maintenance():
        from app.core.database import AsyncSessionLocal
        from app.services.portfolio_snapshot_twr_maintenance_service import maintain_twr_snapshots_for_active_portfolios
        async with AsyncSessionLocal() as db:
            try:
                result = await maintain_twr_snapshots_for_active_portfolios(db)
                logger.info("[scheduler] Snapshots patrimoniais/TWR atualizados: %s", result)
            except Exception as e:
                logger.error("[scheduler] Erro na manutencao de snapshots TWR: %s", e)

    scheduler.start()
    logger.info("Scheduler iniciado — cotações intraday a cada 90 min + Tesouro Direto + benchmarks + proventos diário + pipeline sem eventos + cobertura global de preços + snapshots TWR")
