import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.distributed_job_lock import distributed_job_lock

logger = logging.getLogger(__name__)

SCHEDULER_TIMEZONE = "America/Sao_Paulo"
scheduler = AsyncIOScheduler(timezone=SCHEDULER_TIMEZONE)


def _cron_trigger(**kwargs) -> CronTrigger:
    """Cria gatilhos sempre no fuso operacional do sistema."""
    return CronTrigger(timezone=SCHEDULER_TIMEZONE, **kwargs)


INTL_INTRADAY_HOURS: frozenset[int] = frozenset({11, 14, 17})


def _intraday_asset_types(hour: int) -> list:
    """Retorna classes para o ciclo intradi?rio, reduzindo chamadas externas."""
    from app.models.asset import AssetType

    asset_types = [
        AssetType.ACAO,
        AssetType.FII,
        AssetType.ETF_NACIONAL,
        AssetType.BDR,
        AssetType.CRIPTO,
        AssetType.TESOURO_DIRETO,
    ]
    if hour in INTL_INTRADAY_HOURS:
        asset_types.extend([AssetType.STOCK, AssetType.ETF_INTERNACIONAL])
    return asset_types


def _intraday_quote_triggers() -> tuple[CronTrigger]:
    """Atualiza ativos de pregão de hora em hora, das 09:00 às 18:00."""
    return (_cron_trigger(day_of_week="mon-fri", hour="9-18", minute=0),)


def _crypto_offhours_quote_triggers() -> tuple[CronTrigger, CronTrigger]:
    """Mantém cripto horária fora do pregão e durante fins de semana."""
    return (
        _cron_trigger(day_of_week="mon-fri", hour="0-8,19-23", minute=0),
        _cron_trigger(day_of_week="sat-sun", hour="0-23", minute=0),
    )


def start_scheduler() -> None:
    """Registra sincronizações recorrentes e manutenções locais.

    Regra arquitetural:
    - sincronizações externas recorrentes usam serviços canônicos e leases;
    - preenchimento pontual de lacuna histórica pertence ao resolvedor dedicado
      de preço por data, nunca a jobs amplos de domínio;
    - snapshots/TWR são manutenção local e não consultam providers.
    """

    (intraday_full_hour,) = _intraday_quote_triggers()

    @scheduler.scheduled_job(
        intraday_full_hour,
        id="update_quotes_intraday_full_hour",
        name="Atualizar cotações intradiárias — lote completo (hora cheia)",
        max_instances=1,
        coalesce=True,
    )
    async def update_quotes_intraday():
        from app.core.database import AsyncSessionLocal
        from app.services.quote_cache_invalidation_service import (
            refresh_quotes_and_invalidate,
        )

        current_hour = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE)).hour
        asset_types = _intraday_asset_types(current_hour)
        async with distributed_job_lock(
            job_name="update_quotes_intraday",
            period="intraday",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
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
                    raise

    crypto_offhours_weekdays, crypto_offhours_weekends = (
        _crypto_offhours_quote_triggers()
    )

    @scheduler.scheduled_job(
        crypto_offhours_weekdays,
        id="update_crypto_quotes_offhours_weekdays",
        name="Atualizar cotações de cripto fora do pregão (dias úteis)",
        max_instances=1,
        coalesce=True,
    )
    @scheduler.scheduled_job(
        crypto_offhours_weekends,
        id="update_crypto_quotes_weekends",
        name="Atualizar cotações de cripto aos fins de semana",
        max_instances=1,
        coalesce=True,
    )
    async def update_crypto_quotes_offhours():
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.services.quote_cache_invalidation_service import (
            refresh_quotes_and_invalidate,
        )

        async with distributed_job_lock(
            job_name="update_quotes_intraday",
            period="intraday",
            ttl_seconds=7200,
            status_job_name="update_crypto_quotes",
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                try:
                    updated, invalidated = await refresh_quotes_and_invalidate(
                        db, [AssetType.CRIPTO]
                    )
                    logger.info(
                        "[scheduler] Cripto fora do pregão: %s preços, "
                        "%s carteiras invalidadas",
                        updated,
                        invalidated,
                    )
                except Exception as exc:
                    logger.error(
                        "[scheduler] Erro ao atualizar cotações de cripto "
                        "fora do pregão: %s",
                        exc,
                    )
                    raise

    @scheduler.scheduled_job(
        _cron_trigger(hour=20, minute=45),
        id="persist_daily_close_prices",
        name="Persistir fechamento diário de preços",
        max_instances=1,
        coalesce=True,
    )
    async def persist_daily_close_prices():
        """Persiste diariamente o fechamento dos ativos movimentados em carteira."""
        from sqlalchemy import func, select
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.models.transaction import Transaction
        from app.services.asset_price_global_backfill_service import (
            run_global_asset_price_backfill,
        )

        async with distributed_job_lock(
            job_name="persist_daily_close_prices",
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return

            today = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE)).date()
            is_weekend = today.weekday() >= 5
            try:
                async with AsyncSessionLocal() as db:
                    ticker_query = select(func.upper(func.trim(Transaction.ticker))).distinct()
                    if is_weekend:
                        ticker_query = ticker_query.where(
                            Transaction.asset_type == AssetType.CRIPTO.value
                        )
                    tx_tickers = {
                        ticker
                        for ticker in (await db.execute(ticker_query)).scalars().all()
                        if ticker
                    }
                if is_weekend and not tx_tickers:
                    logger.info(
                        "[scheduler] Fim de semana sem cripto em carteira — fechamento diário ignorado."
                    )
                    return
                result = await run_global_asset_price_backfill(
                    required_to=today,
                    history_start=today,
                    full_history=False,
                    end_grace_days=0,
                    include_start_gaps=False,
                    asset_types={AssetType.CRIPTO.value} if is_weekend else None,
                    tickers=tx_tickers if tx_tickers else None,
                )
                logger.info(
                    "[scheduler] Fechamento diário de preços atualizado: %s",
                    result,
                )
            except Exception as exc:
                logger.error(
                    "[scheduler] Erro ao persistir fechamento diário de preços: %s",
                    exc,
                )
                raise

    async def _run_daily_close_catchup(job_name: str) -> None:
        from datetime import timedelta
        from sqlalchemy import func, select
        from app.core.database import AsyncSessionLocal
        from app.models.asset import AssetType
        from app.models.transaction import Transaction
        from app.services.asset_price_global_backfill_service import (
            run_global_asset_price_backfill,
        )

        async with distributed_job_lock(
            job_name=job_name,
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
            today = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE)).date()
            is_weekend = today.weekday() >= 5
            async with AsyncSessionLocal() as db:
                ticker_query = select(func.upper(func.trim(Transaction.ticker))).distinct()
                if is_weekend:
                    ticker_query = ticker_query.where(
                        Transaction.asset_type == AssetType.CRIPTO.value
                    )
                tx_tickers = {
                    ticker
                    for ticker in (await db.execute(ticker_query)).scalars().all()
                    if ticker
                }
            if is_weekend and not tx_tickers:
                return
            result = await run_global_asset_price_backfill(
                required_to=today,
                history_start=today - timedelta(days=2),
                full_history=False,
                end_grace_days=2,
                include_start_gaps=False,
                asset_types={AssetType.CRIPTO.value} if is_weekend else None,
                tickers=tx_tickers if tx_tickers else None,
            )
            logger.info("[scheduler] Repescagem de fechamento (%s): %s", job_name, result)

    @scheduler.scheduled_job(
        _cron_trigger(hour=22, minute=45),
        id="persist_daily_close_prices_catchup_night",
        name="Repescagem noturna de fechamento de preços (US/FII/Cripto)",
        max_instances=1,
        coalesce=True,
    )
    async def persist_daily_close_prices_catchup_night():
        await _run_daily_close_catchup("persist_daily_close_prices_catchup_night")

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=7, minute=30),
        id="persist_daily_close_prices_catchup_morning",
        name="Repescagem matinal de fechamento de preços (D-1)",
        max_instances=1,
        coalesce=True,
    )
    async def persist_daily_close_prices_catchup_morning():
        await _run_daily_close_catchup("persist_daily_close_prices_catchup_morning")

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour="14,19,21", minute=15),
        id="sync_fx_rates_daily",
        name="Sincronizar taxa PTAX USD-BRL diária",
        max_instances=1,
        coalesce=True,
    )
    async def sync_fx_rates_daily():
        from app.core.database import AsyncSessionLocal
        from app.services.fx_rate_sync_service import sync_usd_brl_fx_rates

        async with distributed_job_lock(
            job_name="sync_fx_rates_daily",
            period="daily",
            ttl_seconds=3600,
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                result = await sync_usd_brl_fx_rates(db)
                logger.info("[scheduler] PTAX USD-BRL atualizada: %s", result)

    if settings.ENABLE_DAILY_BENCHMARK_SYNC:

        @scheduler.scheduled_job(
            _cron_trigger(day_of_week="mon-fri", hour="8,20", minute=40),
            id="sync_benchmark_rates_daily",
            name="Sincronizar índices macroeconômicos (CDI, SELIC, IPCA, IGPM)",
            max_instances=1,
            coalesce=True,
        )
        async def sync_benchmark_rates_daily():
            """Atualiza índices macroeconômicos diários e mensais do SGS/BCB."""
            from app.core.database import AsyncSessionLocal
            from app.models.asset import AssetType
            from app.services.benchmark_rate_service import import_missing_benchmark_history
            from app.services.quote_cache_invalidation_service import invalidate_quote_consumers

            async with distributed_job_lock(
                job_name="sync_benchmark_rates_daily",
                period="daily",
                ttl_seconds=3600,
            ) as acquired:
                if not acquired:
                    return
                async with AsyncSessionLocal() as db:
                    try:
                        stats = await import_missing_benchmark_history(db)
                        await invalidate_quote_consumers(db, asset_types=[AssetType.RENDA_FIXA])
                        logger.info("[scheduler] Índices macroeconômicos atualizados: %s", stats)
                    except Exception as exc:
                        logger.error("[scheduler] Erro ao sincronizar índices macroeconômicos: %s", exc)
                        raise

        @scheduler.scheduled_job(
            _cron_trigger(day_of_week="mon-fri", hour="8,20", minute=42),
            id="sync_ibov_benchmark_daily",
            name="Sincronizar fechamento diário do IBOV (Ibovespa)",
            max_instances=1,
            coalesce=True,
        )
        async def sync_ibov_benchmark_daily():
            """Atualiza fechamento do IBOV em asset_prices."""
            from app.core.database import AsyncSessionLocal
            from app.services.ibov_benchmark_service import sync_ibov_benchmark_prices

            async with distributed_job_lock(
                job_name="sync_ibov_benchmark_daily",
                period="daily",
                ttl_seconds=3600,
            ) as acquired:
                if not acquired:
                    return
                async with AsyncSessionLocal() as db:
                    try:
                        count = await sync_ibov_benchmark_prices(db, range_str="1mo")
                        logger.info("[scheduler] Fechamento do IBOV atualizado: %d registros", count)
                    except Exception as exc:
                        logger.error("[scheduler] Erro ao sincronizar fechamento do IBOV: %s", exc)
                        raise

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

        async with distributed_job_lock(
            job_name="persist_treasury_daily_close",
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                try:
                    await import_treasury_price_history(db, only_missing=True)
                    await update_treasury_latest_prices(db)
                except Exception as exc:
                    logger.error(
                        "[scheduler] Erro no fechamento diário do Tesouro: %s",
                        exc,
                    )
                    raise

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=8, minute=30),
        id="notify_daily_dividend_payments",
        name="Enviar resumo matinal por e-mail dos proventos pagos no dia",
        max_instances=1,
        coalesce=True,
    )
    async def run_daily_dividend_notifications():
        from app.core.database import AsyncSessionLocal
        from app.services.dividend_notification_service import (
            notify_daily_dividend_payments,
        )

        async with distributed_job_lock(
            job_name="notify_daily_dividend_payments",
            period="daily",
            ttl_seconds=3600,
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                try:
                    result = await notify_daily_dividend_payments(db)
                    logger.info(
                        "[scheduler] Notificações de proventos do dia: %s",
                        result,
                    )
                except Exception as exc:
                    logger.error(
                        "[scheduler] Erro ao enviar notificações de proventos: %s",
                        exc,
                    )
                    raise

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-sat", hour=8, minute=0),
        id="sync_asset_dividends_morning",
        name="Sincronizar proventos globais pela manhã",
        max_instances=1,
        coalesce=True,
    )
    async def sync_asset_dividends_morning():
        from app.services.system_bootstrap_dividends_stage import (
            run_system_bootstrap_dividends_stage,
        )
        from app.services.system_bootstrap_execution_context import (
            build_system_bootstrap_execution_context,
        )

        async with distributed_job_lock(
            job_name="sync_asset_dividends",
            period="morning",
            ttl_seconds=21600,
        ) as acquired:
            if not acquired:
                return
            try:
                today = datetime.now(ZoneInfo(SCHEDULER_TIMEZONE)).date()
                context = build_system_bootstrap_execution_context()
                result = await run_system_bootstrap_dividends_stage(
                    context,
                    start_date=today - timedelta(days=90),
                    end_date=today + timedelta(days=365),
                    authorized=True,
                    allow_production_branch=True,
                )
                logger.info("[scheduler] Sincronização de proventos: %s", result)
            except Exception as exc:
                logger.error("[scheduler] Erro na sincronização de proventos: %s", exc)
                raise

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=22, minute=0),
        id="sync_corporate_events_daily",
        name="Sincronizar eventos corporativos globais ao fim do dia",
        max_instances=1,
        coalesce=True,
    )
    async def sync_corporate_events_daily():
        from app.services.system_bootstrap_corporate_events_stage import (
            run_system_bootstrap_corporate_events_stage,
        )
        from app.services.system_bootstrap_execution_context import (
            build_system_bootstrap_execution_context,
        )

        async with distributed_job_lock(
            job_name="sync_corporate_events",
            period="daily",
            ttl_seconds=21600,
        ) as acquired:
            if not acquired:
                return
            try:
                context = build_system_bootstrap_execution_context()
                result = await run_system_bootstrap_corporate_events_stage(
                    context,
                    authorized=True,
                    continue_on_asset_error=True,
                )
                logger.info(
                    "[scheduler] Sincronização de eventos corporativos: %s",
                    result,
                )
            except Exception as exc:
                logger.error(
                    "[scheduler] Erro na sincronização de eventos corporativos: %s",
                    exc,
                )
                raise

    @scheduler.scheduled_job(
        _cron_trigger(hour=21, minute=0),
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

        async with distributed_job_lock(
            job_name="portfolio_snapshot_auto_maintenance",
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
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
                    raise

    @scheduler.scheduled_job(
        _cron_trigger(hour="9,23", minute=5),
        id="portfolio_snapshot_reconcile_late_data",
        name="Reconciliar snapshots TWR após CDI/FX/preços tardios",
        max_instances=1,
        coalesce=True,
    )
    async def portfolio_snapshot_reconcile_late_data():
        from app.core.database import AsyncSessionLocal
        from app.services.portfolio_snapshot_twr_maintenance_service import (
            maintain_twr_snapshots_for_active_portfolios,
        )

        async with distributed_job_lock(
            job_name="portfolio_snapshot_reconcile_late_data",
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                result = await maintain_twr_snapshots_for_active_portfolios(db)
                logger.info(
                    "[scheduler] Reconciliação TWR pós-fechamento/D+1: %s",
                    result,
                )

    @scheduler.scheduled_job(
        _cron_trigger(day_of_week="mon-fri", hour=21, minute=30),
        id="refresh_asset_fundamentals_daily",
        name="Atualizar indicadores fundamentalistas, métricas e consenso de ativos",
        max_instances=1,
        coalesce=True,
    )
    async def refresh_asset_fundamentals_daily():
        """Atualiza indicadores e métricas diárias dos ativos das carteiras e catálogo."""
        from app.core.database import AsyncSessionLocal
        from app.services.asset_fundamentals_refresh_service import (
            run_asset_fundamentals_refresh,
        )

        async with distributed_job_lock(
            job_name="refresh_asset_fundamentals_daily",
            period="daily",
            ttl_seconds=7200,
        ) as acquired:
            if not acquired:
                return
            async with AsyncSessionLocal() as db:
                try:
                    stats = await run_asset_fundamentals_refresh(
                        db, force_refresh=True
                    )
                    logger.info(
                        "[scheduler] Indicadores fundamentalistas atualizados: %s",
                        stats,
                    )
                except Exception as exc:
                    logger.error(
                        "[scheduler] Erro ao atualizar indicadores fundamentalistas: %s",
                        exc,
                    )
                    raise

    if settings.ENABLE_B3_MARKET_CALENDAR_MONTHLY_AUDIT:

        @scheduler.scheduled_job(
            _cron_trigger(day=1, hour=8, minute=15),
            id="audit_b3_market_calendar_monthly",
            name="Auditar mensalmente a fonte oficial do calendario B3",
            max_instances=1,
            coalesce=True,
        )
        async def audit_b3_market_calendar_monthly():
            """Audit the source only; calendar promotion remains manual."""
            from app.core.database import AsyncSessionLocal
            from app.services.b3_market_calendar_audit_service import (
                run_b3_market_calendar_monthly_audit,
            )
            from app.services.b3_market_calendar_configuration_service import (
                resolve_b3_market_calendar_audit_configuration,
            )

            async with distributed_job_lock(
                job_name="audit_b3_market_calendar",
                period="monthly",
                ttl_seconds=300,
            ) as acquired:
                if not acquired:
                    return
                try:
                    async with AsyncSessionLocal() as db:
                        configuration = (
                            await resolve_b3_market_calendar_audit_configuration(
                                db,
                                runtime_settings=settings,
                            )
                        )
                    result = await run_b3_market_calendar_monthly_audit(
                        source_url=configuration.source_url,
                        source_year=configuration.source_year,
                    )
                    logger.info(
                        "[scheduler] Auditoria mensal B3 concluida: "
                        "sha256=%s closed_dates=%s special_dates=%s writes=%s",
                        result.source_sha256,
                        len(result.report.explicitly_closed_dates),
                        len(result.report.special_operation_dates),
                        result.report.database_writes_executed,
                    )
                except Exception as exc:
                    logger.error(
                        "[scheduler] Erro na auditoria mensal do calendario B3: "
                        "%s",
                        exc,
                    )
                    raise

    scheduler.start()
    logger.info(
        "Scheduler iniciado — cotações horárias + fechamentos diários + snapshots locais"
    )
