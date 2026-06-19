"""
Asset Onboarding Service.

Executado como BackgroundTask ao criar um novo ativo (primeira transacao).
Cada etapa e idempotente: so roda se o dado ainda nao existe no banco,
garantindo seguranca em re-execucoes (ex: ativo recriado, falha parcial).

Etapas:
  1. Historico de precos   -> persist_daily_prices (5 anos)
  2. Proventos historicos  -> dividend_backfill_service.run_backfill
  3. Logo URL              -> logo_service.fetch_logo_url -> Asset.logo_url
"""
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.asset_dividend import AssetDividend
from app.services.price_history_service import persist_daily_prices
from app.services.dividend_backfill_service import run_backfill
from app.services.logo_service import fetch_logo_url

logger = logging.getLogger(__name__)

# Janela de historico de precos coletada no onboarding (5 anos)
_PRICE_HISTORY_DAYS = 365 * 5


async def _has_price_history(db: AsyncSession, ticker: str) -> bool:
    """True se ja existe ao menos 1 registro de preco para o ticker."""
    result = await db.execute(
        select(func.count(AssetPrice.id))
        .join(Asset, AssetPrice.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
    )
    count = result.scalar_one_or_none() or 0
    return count > 0


async def _has_dividends(db: AsyncSession, ticker: str) -> bool:
    """True se ja existe ao menos 1 AssetDividend para o ticker."""
    result = await db.execute(
        select(func.count(AssetDividend.id))
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(Asset.ticker == ticker)
    )
    count = result.scalar_one_or_none() or 0
    return count > 0


async def _has_logo(db: AsyncSession, ticker: str) -> bool:
    """True se Asset.logo_url ja esta preenchido."""
    result = await db.execute(
        select(Asset.logo_url).where(Asset.ticker == ticker)
    )
    logo_url = result.scalar_one_or_none()
    return bool(logo_url)


async def _save_logo(db: AsyncSession, ticker: str, url: str) -> None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = result.scalar_one_or_none()
    if asset:
        asset.logo_url = url
        await db.commit()


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

    async with AsyncSessionLocal() as db:
        # ----------------------------------------------------------------
        # Etapa 1: Historico de precos
        # ----------------------------------------------------------------
        if await _has_price_history(db, ticker):
            logger.info(f"[onboarding] {ticker}: historico de precos ja existe — pulando")
        else:
            try:
                n = await persist_daily_prices(db, ticker, at, days_back=_PRICE_HISTORY_DAYS)
                logger.info(f"[onboarding] {ticker}: {n} precos historicos salvos")
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
