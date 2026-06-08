import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.core.database import AsyncSessionLocal
from app.core.cache import cache_set
from app.integrations.brapi import get_quotes_bulk
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.portfolio_position import PortfolioPosition
from app.models.asset import Asset, AssetType
from app.services.corporate_event_service import (
    sync_corporate_events_for_asset, apply_pending_events
)
from app.services.dividend_service import sync_dividends_for_portfolio_position

logger = logging.getLogger(__name__)

BRAPI_ASSET_TYPES = {
    AssetType.ACAO_NACIONAL,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
    AssetType.BDR,
}

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


async def _get_active_brapi_assets() -> list[Asset]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Asset)
            .join(PortfolioPosition, PortfolioPosition.asset_id == Asset.id)
            .where(
                PortfolioPosition.quantity > 0,
                Asset.asset_type.in_(BRAPI_ASSET_TYPES),
            )
            .distinct()
        )
        return result.scalars().all()


async def job_update_quotes():
    """Atualiza cotacoes de todos os ativos nacionais em carteira no Redis."""
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


async def job_sync_corporate_events():
    """
    Detecta eventos corporativos (SPLIT/BONUS) via BRAPI PRO
    e aplica automaticamente em todas as carteiras com o ativo.
    """
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
    """Registra dividendos/proventos de todos os ativos em carteira."""
    logger.info("[Scheduler] Sincronizando proventos...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PortfolioPosition)
            .options(selectinload(PortfolioPosition.asset))
            .where(PortfolioPosition.quantity > 0)
        )
        positions = result.scalars().all()
        total_new = 0
        for position in positions:
            if position.asset.asset_type not in BRAPI_ASSET_TYPES:
                continue
            try:
                total_new += await sync_dividends_for_portfolio_position(db, position)
            except Exception as e:
                logger.error(f"[Scheduler] Erro dividendos {position.asset.ticker}: {e}")
        await db.commit()
    logger.info(f"[Scheduler] {total_new} novos proventos registrados.")


def init_scheduler():
    # Cotacoes: a cada 5 minutos (dias uteis, horario de pregao controlado pelo upstream)
    scheduler.add_job(
        job_update_quotes,
        IntervalTrigger(minutes=5),
        id="update_quotes",
        replace_existing=True,
    )
    # Eventos corporativos: diario as 19h30 (apos fechamento B3)
    scheduler.add_job(
        job_sync_corporate_events,
        CronTrigger(hour=19, minute=30, timezone="America/Sao_Paulo"),
        id="sync_corporate_events",
        replace_existing=True,
    )
    # Dividendos: diario as 20h
    scheduler.add_job(
        job_sync_dividends,
        CronTrigger(hour=20, minute=0, timezone="America/Sao_Paulo"),
        id="sync_dividends",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] 3 jobs registrados e scheduler iniciado.")
