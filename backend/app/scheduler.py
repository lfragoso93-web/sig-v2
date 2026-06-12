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
from app.models.portfolio_position import PortfolioPosition
from app.models.transaction import Transaction
from app.services.corporate_event_service import (
    sync_corporate_events_for_asset, apply_pending_events
)
from app.services.dividend_backfill_service import backfill_dividends

logger = logging.getLogger(__name__)

BRAPI_ASSET_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
}

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")


# ── helpers ─────────────────────────────────────────────────────────────────────────

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


async def _get_active_portfolio_tickers() -> list[tuple[int, str, str]]:
    """
    Retorna lista de (portfolio_id, ticker, asset_type) de todas as posições
    com quantidade > 0 que suportam proventos.
    """
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


# ── Jobs ─────────────────────────────────────────────────────────────────────────────

async def job_update_quotes():
    """Atualiza cotações de todos os ativos nacionais em carteira no Redis."""
    logger.info("[Scheduler] Atualizando cotações...")
    assets = await _get_active_brapi_assets()
    if not assets:
        return
    tickers = [a.brapi_ticker or a.ticker for a in assets]
    quotes = await get_quotes_bulk(tickers)
    for quote in quotes:
        ticker = quote.get("symbol", "")
        if ticker:
            await cache_set(f"quote:{ticker}", quote, ttl=360)
    logger.info(f"[Scheduler] {len(quotes)} cotações atualizadas.")


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
    """
    Ressincroniza proventos de todos os (portfolio, ticker) ativos no sistema.
    Cobre nacionais (BRAPI) e internacionais (yfinance).
    Roda semanalmente aos domingos às 02:00 — custo alto mas fora do pregao.
    """
    logger.info("[Scheduler] Resync semanal de proventos iniciado...")
    portfolio_tickers = await _get_active_portfolio_tickers()

    total_processed = 0
    for portfolio_id, ticker, asset_type in portfolio_tickers:
        try:
            async with AsyncSessionLocal() as db:
                await backfill_dividends(
                    db           = db,
                    portfolio_id = portfolio_id,
                    ticker       = ticker,
                    asset_type   = asset_type,
                )
            total_processed += 1
        except Exception as e:
            logger.error(f"[Scheduler] Erro resync proventos {ticker}: {e}")

    logger.info(f"[Scheduler] Resync semanal concluído: {total_processed} posições processadas.")


async def job_update_dividend_status():
    """
    Atualiza status A_RECEBER → RECEBIDO para proventos cujo
    payment_date já passou. Roda diariamente às 08:00.
    Leve: apenas um UPDATE no banco, sem chamadas externas.
    """
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


# ── Init ──────────────────────────────────────────────────────────────────────────────

def init_scheduler():
    # Cotações: a cada 5 minutos
    scheduler.add_job(
        job_update_quotes,
        IntervalTrigger(minutes=5),
        id="update_quotes",
        replace_existing=True,
    )

    # Eventos corporativos: diário às 19h30 (após fechamento B3)
    scheduler.add_job(
        job_sync_corporate_events,
        CronTrigger(hour=19, minute=30, timezone="America/Sao_Paulo"),
        id="sync_corporate_events",
        replace_existing=True,
    )

    # Resync completo de proventos: semanal (domingo 02:00)
    # Custo alto (muitas chamadas externas) — roda fora do horário nobre
    scheduler.add_job(
        job_sync_dividends,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="America/Sao_Paulo"),
        id="sync_dividends",
        replace_existing=True,
    )

    # Atualiza status A_RECEBER → RECEBIDO: diário às 08:00
    # Leve — apenas um UPDATE no banco
    scheduler.add_job(
        job_update_dividend_status,
        CronTrigger(hour=8, minute=0, timezone="America/Sao_Paulo"),
        id="update_dividend_status",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] 4 jobs registrados e scheduler iniciado.")
