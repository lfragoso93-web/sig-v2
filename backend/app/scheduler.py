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
from app.services.quotes_service import update_all_quotes
from app.services.portfolio_snapshot_service import refresh_today_snapshot

logger = logging.getLogger(__name__)

BRAPI_ASSET_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
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

    logger.info("[Scheduler] %d cotacoes atualizadas, %d erros de cache.", ok, errors)


async def job_persist_price_history():
    """
    Atualiza o historico de precos de todos os ativos (incremental).

    Usa run_incremental_update do backfill service, que busca apenas
    o delta desde o last_ts de cada ativo — no maximo 7 dias de window.
    Roda diariamente apos o fechamento do mercado (18h30 BRT).
    """
    logger.info("[Scheduler] Iniciando atualizacao incremental de precos...")
    try:
        from app.services.price_history_backfill_service import run_incremental_update
        await run_incremental_update()
    except Exception as e:
        logger.error("[Scheduler] job_persist_price_history: erro: %s", e)


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
        "[Scheduler] Snapshots do dia: %d ok, %d erros (%d carteiras ativas).",
        ok, errors, len(portfolio_ids)
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

    logger.info("[Scheduler] %d novos eventos, %d aplicados nas carteiras.", new_total, applied)


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
        "[Scheduler] Resync semanal concluido: %d ok, %d erros.",
        total_processed, errors
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
        logger.info("[Scheduler] %d proventos marcados como RECEBIDO.", updated)
    except Exception as e:
        logger.error("[Scheduler] job_update_dividend_status: erro: %s", e)


async def job_seed_assets():
    """
    Seed semanal de ativos da B3 via BRAPI /v2/tickers.
    Roda toda segunda-feira as 3h para capturar novos IPOs.
    """
    logger.info("[Scheduler] Iniciando seed semanal de ativos da B3...")
    try:
        from app.services.asset_seed_service import run_asset_seed
        async with AsyncSessionLocal() as db:
            result = await run_asset_seed(db)
        logger.info(
            "[Scheduler] Seed concluido: %s criados, %s atualizados, %s sem mudanca, %s erros. Por tipo: %s",
            result.created, result.updated, result.skipped, result.errors, result.by_type,
        )
    except Exception as e:
        logger.error("[Scheduler] job_seed_assets: falha geral: %s", e)


async def job_sync_fii_dividends():
    """
    Sync semanal de dividendos de FIIs via BRAPI /v2/funds/dividends.

    Roda todo sabado as 6h BRT em modo incremental (cursor de 30 dias de overlap).
    Complementar ao job_sync_dividends (domingo 2h) que trata acoes/ETFs/BDRs.
    Falha isolada — nao afeta outros jobs.
    """
    logger.info("[Scheduler] job_sync_fii_dividends: iniciando sync de dividendos FII...")
    try:
        from app.services.dividends_sync_service import run_fii_dividends_sync
        async with AsyncSessionLocal() as db:
            result = await run_fii_dividends_sync(db)
        logger.info(
            "[Scheduler] job_sync_fii_dividends: concluido — "
            "tickers=%s upserted=%s created=%s updated=%s errors=%s",
            result.get("tickers_processed", 0),
            result.get("upserted", 0),
            result.get("created", 0),
            result.get("updated", 0),
            result.get("errors", 0),
        )
    except Exception as e:
        logger.error("[Scheduler] job_sync_fii_dividends: falha geral: %s", e)


def init_scheduler():
    scheduler.add_job(
        job_update_quotes,
        IntervalTrigger(minutes=5),
        id="update_quotes",
        replace_existing=True,
    )
    # Incremental de precos: todo dia apos fechamento da B3 (18h30 BRT)
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
    scheduler.add_job(
        job_seed_assets,
        CronTrigger(day_of_week="mon", hour=3, minute=0, timezone="America/Sao_Paulo"),
        id="seed_assets",
        replace_existing=True,
    )
    # Sync semanal de dividendos de FIIs via BRAPI: sabado 6h BRT
    scheduler.add_job(
        job_sync_fii_dividends,
        CronTrigger(day_of_week="sat", hour=6, minute=0, timezone="America/Sao_Paulo"),
        id="sync_fii_dividends",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] 8 jobs registrados e scheduler iniciado.")
