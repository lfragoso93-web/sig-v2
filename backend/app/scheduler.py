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
from app.services.quotes_service import update_all_quotes  # canônico com cache L1/L2/L3
from app.services.portfolio_snapshot_service import refresh_today_snapshot

logger = logging.getLogger(__name__)

# Tipos atendidos por BRAPI (inclui BDR — negocia na B3)
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
    """Retorna ativos BR ativos via Transaction (sem depender de PortfolioPosition legada)."""
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
    logger.info("[Scheduler] Atualizando cotacoes...")
    assets = await _get_active_brapi_assets()
    if not assets:
        return
    tickers = [a.brapi_ticker or a.ticker for a in assets]
    quotes = await get_quotes_bulk(tickers)
    for quote in quotes:
        ticker = quote.get("symbol", "")
        if ticker:
            await cache_set(f"quote:{ticker}", quote, ttl=360)
    logger.info(f"[Scheduler] {len(quotes)} cotacoes atualizadas.")


async def job_persist_price_history():
    logger.info("[Scheduler] Persistindo historico de precos...")
    pairs = await _get_price_history_tickers()
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
            logger.error(f"[Scheduler] Erro persist price {ticker}: {e}")

    logger.info(f"[Scheduler] Historico: {total} registros inseridos, {errors} erros.")


async def job_update_all_quotes_and_snapshots():
    logger.info("[Scheduler] Iniciando update_all_quotes + snapshots do dia...")

    try:
        async with AsyncSessionLocal() as db:
            await update_all_quotes(db)  # quotes_service — canonico com cache L1/L2/L3
        logger.info("[Scheduler] update_all_quotes concluido.")
    except Exception as e:
        logger.error(f"[Scheduler] Erro em update_all_quotes: {e}")

    portfolio_ids = await _get_active_portfolio_ids()
    ok = 0
    errors = 0
    for pid in portfolio_ids:
        try:
            async with AsyncSessionLocal() as db:
                await refresh_today_snapshot(db, pid)
            ok += 1
        except Exception as e:
            errors += 1
            logger.error(f"[Scheduler] Erro snapshot portfolio={pid}: {e}")

    logger.info(
        f"[Scheduler] Snapshots do dia: {ok} ok, {errors} erros "
        f"({len(portfolio_ids)} carteiras ativas)."
    )


async def job_sync_corporate_events():
    logger.info("[Scheduler] Sincronizando eventos corporativos...")
    assets = await _get_active_brapi_assets()
    async with AsyncSessionLocal() as db:
        new_total = 0
        for asset in assets:
            try:
                new_events = await sync_corporate_events_for_asset(db, asset)
                new_total += len(new_events)
            except Exception as e:
                logger.error(f"[Scheduler] Erro sync {asset.ticker}: {e}")
        applied = await apply_pending_events(db)
        await db.commit()
    logger.info(f"[Scheduler] {new_total} novos eventos, {applied} aplicados nas carteiras.")


async def job_sync_dividends():
    logger.info("[Scheduler] Resync semanal de proventos iniciado...")
    portfolio_tickers = await _get_active_portfolio_tickers()

    total_processed = 0
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
            logger.error(f"[Scheduler] Erro resync proventos {ticker}: {e}")

    logger.info(f"[Scheduler] Resync semanal concluido: {total_processed} posicoes processadas.")


async def job_update_dividend_status():
    today = date.today()
    logger.info("[Scheduler] Atualizando status de proventos para RECEBIDO...")
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
