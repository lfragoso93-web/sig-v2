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
from app.models.portfolio_position import PortfolioPosition
from app.models.transaction import Transaction
from app.services.corporate_event_service import (
    sync_corporate_events_for_asset, apply_pending_events
)
from app.services.dividend_backfill_service import backfill_dividends
from app.services.price_history_service import persist_daily_prices
from app.services.quote_service import update_all_quotes
from app.services.portfolio_snapshot_service import refresh_today_snapshot

logger = logging.getLogger(__name__)

BRAPI_ASSET_TYPES = {
    AssetType.ACAO,
    AssetType.FII,
    AssetType.ETF_NACIONAL,
}

# Tipos que suportam historico via yfinance
PRICE_HISTORY_TYPES = {
    AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL,
    AssetType.STOCK, AssetType.ETF_INTERNACIONAL,
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
    Retorna lista de (portfolio_id, ticker, asset_type) de todas as posicoes
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


async def _get_price_history_tickers() -> list[tuple[str, AssetType]]:
    """Retorna (ticker, asset_type) distintos que suportam historico de preco."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Transaction.ticker, Transaction.asset_type).distinct()
        )
        rows = result.all()
    return [
        (r.ticker, r.asset_type)
        for r in rows
        if r.ticker and AssetType(r.asset_type) in PRICE_HISTORY_TYPES
    ]


async def _get_active_portfolio_ids() -> list[int]:
    """Retorna IDs de todas as carteiras ativas com pelo menos 1 transacao."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Portfolio.id)
            .join(Transaction, Transaction.portfolio_id == Portfolio.id)
            .where(Portfolio.is_active == True)
            .distinct()
        )
        return [row.id for row in result.all()]


# ── Jobs ────────────────────────────────────────────────────────────────────────

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


async def job_persist_price_history():
    """
    Persiste o fechamento diario de todos os ativos com historico suportado.
    Roda apos o fechamento do mercado (18h30 Sao Paulo).
    Usa INSERT ON CONFLICT DO NOTHING — idempotente.
    """
    logger.info("[Scheduler] Persistindo historico de precos...")
    pairs = await _get_price_history_tickers()
    if not pairs:
        logger.info("[Scheduler] Nenhum ativo para historico de precos.")
        return

    total = 0
    errors = 0
    for ticker, asset_type_str in pairs:
        try:
            asset_type = AssetType(asset_type_str)
            async with AsyncSessionLocal() as db:
                inserted = await persist_daily_prices(
                    db, ticker, asset_type, days_back=2  # apenas ontem + hoje
                )
                total += inserted
        except Exception as e:
            errors += 1
            logger.error(f"[Scheduler] Erro persist price {ticker}: {e}")

    logger.info(f"[Scheduler] Historico: {total} registros inseridos, {errors} erros.")


async def job_update_all_quotes_and_snapshots():
    """
    Job diario (19h00, apos fechamento B3):
      1. Atualiza Asset.last_price de todos os ativos (update_all_quotes).
      2. Gera/atualiza o snapshot do dia para cada carteira ativa
         (refresh_today_snapshot).

    Ordem importa: cotacoes primeiro, snapshot depois —
    o snapshot usa Asset.last_price como fallback se AssetPrice ainda nao
    tiver o fechamento do dia atual.
    """
    logger.info("[Scheduler] Iniciando update_all_quotes + snapshots do dia...")

    # Passo 1: atualiza cotacoes de todos os ativos
    try:
        async with AsyncSessionLocal() as db:
            await update_all_quotes(db)
        logger.info("[Scheduler] update_all_quotes concluido.")
    except Exception as e:
        logger.error(f"[Scheduler] Erro em update_all_quotes: {e}")

    # Passo 2: snapshot diario de cada carteira ativa
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
    Roda semanalmente aos domingos as 02:00 - custo alto mas fora do pregao.
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

    logger.info(f"[Scheduler] Resync semanal concluido: {total_processed} posicoes processadas.")


async def job_update_dividend_status():
    """
    Atualiza status A_RECEBER -> RECEBIDO para proventos cujo
    payment_date ja passou. Roda diariamente as 08:00.
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


# ── Init ───────────────────────────────────────────────────────────────────────────

def init_scheduler():
    # Cotacoes Redis: a cada 5 minutos
    scheduler.add_job(
        job_update_quotes,
        IntervalTrigger(minutes=5),
        id="update_quotes",
        replace_existing=True,
    )

    # Historico de precos: diario as 18h30 (apos fechamento B3)
    scheduler.add_job(
        job_persist_price_history,
        CronTrigger(hour=18, minute=30, timezone="America/Sao_Paulo"),
        id="persist_price_history",
        replace_existing=True,
    )

    # Cotacoes DB (last_price) + snapshots diarios: 19h00
    # Roda 30min apos persist_price_history para garantir que AssetPrice
    # do dia ja esta salvo antes de calcular o snapshot.
    scheduler.add_job(
        job_update_all_quotes_and_snapshots,
        CronTrigger(hour=19, minute=0, timezone="America/Sao_Paulo"),
        id="update_all_quotes_and_snapshots",
        replace_existing=True,
    )

    # Eventos corporativos: diario as 19h30 (apos fechamento B3)
    scheduler.add_job(
        job_sync_corporate_events,
        CronTrigger(hour=19, minute=30, timezone="America/Sao_Paulo"),
        id="sync_corporate_events",
        replace_existing=True,
    )

    # Resync completo de proventos: semanal (domingo 02:00)
    scheduler.add_job(
        job_sync_dividends,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="America/Sao_Paulo"),
        id="sync_dividends",
        replace_existing=True,
    )

    # Atualiza status A_RECEBER -> RECEBIDO: diario as 08:00
    scheduler.add_job(
        job_update_dividend_status,
        CronTrigger(hour=8, minute=0, timezone="America/Sao_Paulo"),
        id="update_dividend_status",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] 6 jobs registrados e scheduler iniciado.")
