import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.core.cache import cache_set
from app.integrations.brapi import get_quotes_bulk
from app.models.asset import Asset, AssetType
from app.models.dividend import Dividend, DividendStatus
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
from app.services.corporate_event_service import (
    sync_corporate_events_for_asset, apply_pending_events
)
from app.services.dividend_backfill_service import backfill_dividends
from app.services.price_history_service import persist_daily_prices
from app.services.quotes_service import update_all_quotes
from app.services.portfolio_snapshot_service import refresh_today_snapshot

logger = logging.getLogger(__name__)

BRAPI_ASSET_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
}

PRICE_HISTORY_TYPES = {
    AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL,
    AssetType.BDR,
    AssetType.STOCK, AssetType.ETF_INTERNACIONAL,
}

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


async def _get_active_brapi_assets() -> list[Asset]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Asset)
            .join(Transaction, Transaction.ticker == Asset.ticker)
            .where(
                Asset.asset_type.in_([t.value for t in BRAPI_ASSET_TYPES]),
            )
            .distinct()
        )
        return result.scalars().all()


async def _get_active_portfolio_tickers() -> list[tuple[int, str, str]]:
    skip = {AssetType.CRIPTO.value, AssetType.TESOURO_DIRETO.value, AssetType.RENDA_FIXA.value}
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(
                Transaction.portfolio_id,
                Transaction.ticker,
                Transaction.asset_type,
            )
            .distinct()
        )
        rows = result.all()

    return [
        (r.portfolio_id, r.ticker, r.asset_type)
        for r in rows
        if r.asset_type not in skip and r.ticker
    ]


async def _get_price_history_tickers() -> list[tuple[str, AssetType]]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction.ticker, Transaction.asset_type).distinct()
        )
        rows = result.all()
    return [
        (r.ticker, AssetType(r.asset_type))
        for r in rows
        if r.ticker and AssetType(r.asset_type) in PRICE_HISTORY_TYPES
    ]


async def _get_active_portfolio_ids() -> list[int]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Portfolio.id)
            .join(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.is_active.is_(True))
            .distinct()
        )
        return [row.id for row in result.all()]


async def job_update_quotes():
    """Atualiza cotacoes BR via BRAPI. Falha por ativo e isolada."""
    logger.info("[Scheduler] Atualizando cotacoes...")
    try:
        assets = await _get_active_brapi_assets()
    except Exception as e:
        logger.error("[Scheduler] job_update_quotes: erro ao listar ativos: %s", e)
        return

    if not assets:
        return

    tickers = [a.brapi_ticker or a.ticker for a in assets]
    try:
        quotes = await get_quotes_bulk(tickers)
    except Exception as e:
        logger.error("[Scheduler] job_update_quotes: erro BRAPI bulk: %s", e)
        return

    ok = 0
    errors = 0
    for quote in quotes:
        ticker = quote.get("symbol", "")
        if not ticker:
            continue
        try:
            await cache_set(f"quote:{ticker}", quote, ttl=360)
            ok += 1
        except Exception as e:
            errors += 1
            logger.warning("[Scheduler] job_update_quotes: erro cache %s: %s", ticker, e)

    logger.info(f"[Scheduler] {ok} cotacoes atualizadas, {errors} erros de cache.")


async def job_persist_price_history():
    """Persiste historico de precos. Falha por ticker e isolada."""
    logger.info("[Scheduler] Persistindo historico de precos...")
    try:
        pairs = await _get_price_history_tickers()
    except Exception as e:
        logger.error("[Scheduler] job_persist_price_history: erro ao listar tickers: %s", e)
        return

    if not pairs:
        logger.info("[Scheduler] Nenhum ativo para historico de precos.")
        return

    total = 0
    errors = 0
    for ticker, asset_type in pairs:
        try:
            async with AsyncSessionLocal() as db:
                inserted = await persist_daily_prices(
                    db, ticker, asset_type, days_back=2
                )
                total += inserted
        except Exception as e:
            errors += 1
            logger.error("[Scheduler] Erro persist price %s: %s", ticker, e)

    logger.info(f"[Scheduler] Historico: {total} registros inseridos, {errors} erros.")


async def job_update_all_quotes_and_snapshots():
    """Atualiza todas as cotacoes (L1/L2/L3) e snapshots do dia. Falha por portfolio e isolada."""
    logger.info("[Scheduler] Iniciando update_all_quotes + snapshots do dia...")

    try:
        async with AsyncSessionLocal() as db:
            await update_all_quotes(db)
        logger.info("[Scheduler] update_all_quotes concluido.")
    except Exception as e:
        logger.error("[Scheduler] Erro em update_all_quotes: %s", e)

    try:
        portfolio_ids = await _get_active_portfolio_ids()
    except Exception as e:
        logger.error("[Scheduler] Erro ao listar portfolio_ids para snapshot: %s", e)
        return

    ok = 0
    errors = 0
    for pid in portfolio_ids:
        try:
            async with AsyncSessionLocal() as db:
                await refresh_today_snapshot(db, pid)
            ok += 1
        except Exception as e:
            errors += 1
            logger.error("[Scheduler] Erro snapshot portfolio=%s: %s", pid, e)

    logger.info(
        f"[Scheduler] Snapshots do dia: {ok} ok, {errors} erros "
        f"({len(portfolio_ids)} carteiras ativas)."
    )


async def job_sync_corporate_events():
    """Sincroniza eventos corporativos. Falha por ativo e isolada."""
    logger.info("[Scheduler] Sincronizando eventos corporativos...")
    try:
        assets = await _get_active_brapi_assets()
    except Exception as e:
        logger.error("[Scheduler] job_sync_corporate_events: erro ao listar ativos: %s", e)
        return

    async with AsyncSessionLocal() as db:
        new_total = 0
        for asset in assets:
            try:
                new_events = await sync_corporate_events_for_asset(db, asset)
                new_total += len(new_events)
            except Exception as e:
                logger.error("[Scheduler] Erro sync corporate %s: %s", asset.ticker, e)
        try:
            applied = await apply_pending_events(db)
            await db.commit()
        except Exception as e:
            logger.error("[Scheduler] Erro apply_pending_events: %s", e)
            applied = 0

    logger.info(f"[Scheduler] {new_total} novos eventos, {applied} aplicados nas carteiras.")


async def job_sync_dividends():
    """Resync semanal de proventos. Falha por (portfolio, ticker) e isolada."""
    logger.info("[Scheduler] Resync semanal de proventos iniciado...")
    try:
        portfolio_tickers = await _get_active_portfolio_tickers()
    except Exception as e:
        logger.error("[Scheduler] job_sync_dividends: erro ao listar tickers: %s", e)
        return

    total_processed = 0
    errors = 0
    for portfolio_id, ticker, asset_type in portfolio_tickers:
        try:
            async with AsyncSessionLocal() as db:
                await backfill_dividends(
                    db=db,
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    asset_type=asset_type,
                )
            total_processed += 1
        except Exception as e:
            errors += 1
            logger.error("[Scheduler] Erro resync proventos %s: %s", ticker, e)

    logger.info(
        f"[Scheduler] Resync semanal concluido: {total_processed} ok, {errors} erros."
    )


async def job_update_dividend_status():
    """Marca proventos cujo payment_date ja passou como RECEBIDO."""
    today = date.today()
    logger.info("[Scheduler] Atualizando status de proventos para RECEBIDO...")
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(Dividend)
                .where(
                    Dividend.status == DividendStatus.A_RECEBER,
                    Dividend.payment_date <= today,
                    Dividend.payment_date.isnot(None),
                )
                .values(status=DividendStatus.RECEBIDO)
            )
            await db.commit()
            updated = result.rowcount
        logger.info(f"[Scheduler] {updated} proventos marcados como RECEBIDO.")
    except Exception as e:
        logger.error("[Scheduler] job_update_dividend_status: erro: %s", e)


def init_scheduler():
    scheduler.add_job(
        job_update_quotes,
        IntervalTrigger(minutes=5),
        id="update_quotes",
        replace_existing=True,
    )
    scheduler.add_job(
        job_persist_price_history,
        CronTrigger(hour=18, minute=30, timezone="America/Sao_Paulo"),
        id="persist_price_history",
        replace_existing=True,
    )
    scheduler.add_job(
        job_update_all_quotes_and_snapshots,
        CronTrigger(hour=19, minute=0, timezone="America/Sao_Paulo"),
        id="update_all_quotes_and_snapshots",
        replace_existing=True,
    )
    scheduler.add_job(
        job_sync_corporate_events,
        CronTrigger(hour=19, minute=30, timezone="America/Sao_Paulo"),
        id="sync_corporate_events",
        replace_existing=True,
    )
    scheduler.add_job(
        job_sync_dividends,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="America/Sao_Paulo"),
        id="sync_dividends",
        replace_existing=True,
    )
    scheduler.add_job(
        job_update_dividend_status,
        CronTrigger(hour=8, minute=0, timezone="America/Sao_Paulo"),
        id="update_dividend_status",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] 6 jobs registrados e scheduler iniciado.")
