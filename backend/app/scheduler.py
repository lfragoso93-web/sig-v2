import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.cache import cache_set
from app.integrations.brapi import fetch_quotes_with_meta
from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction
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
        quotes = await fetch_quotes_with_meta(tickers)
    except Exception as e:
        logger.error("[Scheduler] job_update_quotes: erro BRAPI bulk: %s", e)
        return

    ok = 0
    errors = 0
    for ticker, metadata in quotes.items():
        quote = {"symbol": ticker, **metadata}
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


def init_scheduler():
    """Registra somente manutencoes recorrentes permitidas pela politica DB-first."""
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
    scheduler.start()
    logger.info("[Scheduler] 3 jobs permitidos registrados e scheduler iniciado.")
