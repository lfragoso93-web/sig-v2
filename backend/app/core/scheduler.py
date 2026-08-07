import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

SCHEDULER_TIMEZONE = "America/Sao_Paulo"
scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)


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
    """Registra somente preços recorrentes e manutenções locais.

    Regra arquitetural:
    - catálogo, metadados, Proventos, eventos, benchmarks e demais dados externos
      pertencem ao bootstrap completo executado antes da liberação do ambiente;
    - após o bootstrap, providers externos recorrentes são permitidos somente
      para preço intraday e fechamento diário;
    - preenchimento pontual de lacuna histórica pertence ao resolvedor dedicado
      de preço por data, nunca a jobs amplos de domínio;
    - snapshots/TWR são manutenção local e não consultam providers.
    """

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
        from app.services.quote_cache_invalidation_service import (
            refresh_quotes_and_invalidate,
        )

        asset_types = [
            AssetType.ACAO,
            AssetType.FII,
            AssetType.ETF_NACIONAL,
            AssetType.BDR,
            AssetType.STOCK,
            AssetType.ETF_INTERNACIONAL,
            AssetType.CRIPTO,
            AssetType.TESOURO_DIRETO,
        ]
        async with AsyncSessionLocal() as db:
            try:
                updated, invalidated = await refresh_quotes_and_invalidate(
                    db, asset_types
                )
                logger.info(
                    "[scheduler] Intraday: %s preços, %s carteiras invalidadas",
                    updated,
                    invalidated,
                )
            except Exception as exc:
                logger.error(
                    "[scheduler] Erro ao atualizar cotações intradiárias: %s",
                    exc,
                )

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=20, minute=45),
        id="persist_daily_close_prices",
        name="Persistir fechamento diário e preencher lacunas de preços",
        max_instances=1,
        coalesce=True,
    )
    async def persist_daily_close_prices():
        """Persiste somente dados de preço; nenhum outro domínio é sincronizado."""
        from app.services.asset_price_global_backfill_service import (
            run_global_asset_price_backfill,
        )

        try:
            result = await run_global_asset_price_backfill()
            logger.info("[scheduler] Fechamento diário de preços atualizado: %s", result)
        except Exception as exc:
            logger.error(
                "[scheduler] Erro ao persistir fechamento diário de preços: %s",
                exc,
            )

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=20, minute=50),
        id="persist_treasury_daily_close",
        name="Persistir fechamento diário do Tesouro Direto",
        max_instances=1,
        coalesce=True,
    )
    async def persist_treasury_daily_close():
        """Atualiza exclusivamente a série de preços persistida do Tesouro."""
        from app.core.database import AsyncSessionLocal
        from app.services.treasury_price_history_service import (
            import_treasury_price_history,
            update_treasury_latest_prices,
        )

        async with AsyncSessionLocal() as db:
            try:
                await import_treasury_price_history(db, only_missing=True)
                await update_treasury_latest_prices(db)
            except Exception as exc:
                logger.error(
                    "[scheduler] Erro no fechamento diário do Tesouro: %s",
                    exc,
                )

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=21, minute=0),
        id="portfolio_snapshot_auto_maintenance",
        name="Manutenção automática de snapshots patrimoniais e TWR",
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
                logger.info(
                    "[scheduler] Snapshots patrimoniais/TWR atualizados: %s",
                    result,
                )
            except Exception as exc:
                logger.error(
                    "[scheduler] Erro na manutenção de snapshots TWR: %s",
                    exc,
                )

    scheduler.start()
    logger.info(
        "Scheduler iniciado — preços intraday + fechamentos diários + snapshots locais"
    )
