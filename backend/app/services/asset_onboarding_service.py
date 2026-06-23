"""
Asset Onboarding Service.

Executado como BackgroundTask ao criar um novo ativo (primeira transacao).
Cada etapa e idempotente: so roda se o dado ainda nao existe no banco,
garantindo seguranca em re-execucoes (ex: ativo recriado, falha parcial).

Etapas:
  1. Historico de precos   -> BRAPI Pro range=max (BR) / persist_daily_prices 5a (INTL)
  2. Proventos historicos  -> dividend_backfill_service.run_backfill
  3. Logo URL              -> logo_service.fetch_logo_url -> Asset.logo_url
"""
import logging
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.asset_types import INTL_TYPES
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.asset_dividend import AssetDividend
from app.services.price_history_service import persist_daily_prices, upsert_daily_prices
from app.services.dividend_backfill_service import run_backfill
from app.services.logo_service import fetch_logo_url
from app.integrations.brapi import fetch_price_history_full

logger = logging.getLogger(__name__)

# Janela de fallback para ativos internacionais (yfinance nao tem range=max equivalente).
_PRICE_HISTORY_DAYS_INTL = 365 * 5


async def _has_price_history(db: AsyncSession, ticker: str) -> bool:
    result = await db.execute(
        select(func.count(AssetPrice.id))
        .join(Asset, AssetPrice.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
    )
    return (result.scalar_one_or_none() or 0) > 0


async def _has_dividends(db: AsyncSession, ticker: str) -> bool:
    result = await db.execute(
        select(func.count(AssetDividend.id))
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
    )
    return (result.scalar_one_or_none() or 0) > 0


async def _has_logo(db: AsyncSession, ticker: str) -> bool:
    result = await db.execute(
        select(Asset.logo_url).where(Asset.ticker == ticker)
    )
    return bool(result.scalar_one_or_none())


async def _save_logo(db: AsyncSession, ticker: str, url: str) -> None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = result.scalar_one_or_none()
    if asset:
        asset.logo_url = url
        await db.commit()


async def _onboard_price_history_br(db: AsyncSession, ticker: str) -> None:
    """
    Coleta historico completo via BRAPI Pro (range=max) e persiste no banco.
    Disponivel apenas no plano Pro — sem limite de anos.
    """
    rows = await fetch_price_history_full(ticker)
    if not rows:
        logger.warning(f"[onboarding] {ticker}: BRAPI range=max retornou vazio — sem historico salvo")
        return

    # Converte para o formato esperado por upsert_daily_prices: list[(date, float)]
    daily_rows = [
        (dt.date() if isinstance(dt, datetime) else dt, close)
        for dt, close in rows
    ]
    n = await upsert_daily_prices(db, ticker, daily_rows)
    logger.info(f"[onboarding] {ticker}: {n} precos historicos salvos via range=max ({len(rows)} registros brutos)")


async def run_onboarding(ticker: str, asset_type: str) -> None:
    """
    Ponto de entrada do onboarding. Abre sua propria sessao de banco
    para nao interferir na sessao do request original.

    Chamado via FastAPI BackgroundTasks:
        background_tasks.add_task(run_onboarding, ticker, asset_type)
    """
    logger.info(f"[onboarding] iniciando para {ticker} ({asset_type})")

    try:
        at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
    except ValueError:
        logger.warning(f"[onboarding] asset_type invalido: {asset_type} — abortando")
        return

    is_intl = at in INTL_TYPES

    async with AsyncSessionLocal() as db:
        # ----------------------------------------------------------------
        # Etapa 1: Historico de precos
        # ----------------------------------------------------------------
        if await _has_price_history(db, ticker):
            logger.info(f"[onboarding] {ticker}: historico de precos ja existe — pulando")
        else:
            try:
                if is_intl:
                    # Ativos internacionais: yfinance com janela de 5 anos
                    n = await persist_daily_prices(db, ticker, at, days_back=_PRICE_HISTORY_DAYS_INTL)
                    logger.info(f"[onboarding] {ticker}: {n} precos historicos salvos (INTL, {_PRICE_HISTORY_DAYS_INTL}d)")
                else:
                    # Ativos nacionais: BRAPI Pro range=max (historico completo)
                    await _onboard_price_history_br(db, ticker)
            except Exception as e:
                logger.error(f"[onboarding] {ticker}: falha ao salvar precos historicos: {e}")

        # ----------------------------------------------------------------
        # Etapa 2: Proventos historicos
        # ----------------------------------------------------------------
        if await _has_dividends(db, ticker):
            logger.info(f"[onboarding] {ticker}: proventos ja existem — pulando")
        else:
            try:
                await run_backfill(db, ticker, at)
                logger.info(f"[onboarding] {ticker}: proventos historicos salvos")
            except Exception as e:
                logger.error(f"[onboarding] {ticker}: falha ao salvar proventos: {e}")

        # ----------------------------------------------------------------
        # Etapa 3: Logo
        # ----------------------------------------------------------------
        if await _has_logo(db, ticker):
            logger.info(f"[onboarding] {ticker}: logo ja existe — pulando")
        else:
            try:
                url = await fetch_logo_url(ticker, at)
                if url:
                    await _save_logo(db, ticker, url)
                    logger.info(f"[onboarding] {ticker}: logo salvo: {url}")
                else:
                    logger.warning(f"[onboarding] {ticker}: logo nao encontrado em nenhuma fonte")
            except Exception as e:
                logger.error(f"[onboarding] {ticker}: falha ao salvar logo: {e}")

    logger.info(f"[onboarding] {ticker}: concluido")
