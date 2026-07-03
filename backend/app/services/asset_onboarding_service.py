"""
Asset Onboarding Service.

Executado como BackgroundTask ao criar um novo ativo (primeira transacao).

Ativos em NO_QUOTE_TYPES, como RENDA_FIXA, não possuem ticker de mercado e não
podem passar por BRAPI/yfinance/logo/proventos. Para esses tipos, o onboarding
é encerrado imediatamente.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.asset_types import INTL_TYPES, NO_QUOTE_TYPES
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.asset_dividend import AssetDividend
from app.services.price_history_service import persist_daily_prices
from app.services.dividend_backfill_service import run_backfill
from app.services.logo_service import fetch_logo_url
from app.integrations.brapi import fetch_price_history_full

logger = logging.getLogger(__name__)

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
    result = await db.execute(select(Asset.logo_url).where(Asset.ticker == ticker))
    return bool(result.scalar_one_or_none())


async def _save_logo(db: AsyncSession, ticker: str, url: str) -> None:
    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = result.scalar_one_or_none()
    if asset:
        asset.logo_url = url
        await db.commit()


async def _upsert_price_row(db: AsyncSession, asset_id: int, timestamp: datetime, close: float, source: str = "brapi") -> None:
    stmt = (
        pg_insert(AssetPrice)
        .values(
            asset_id=asset_id,
            timestamp=timestamp,
            close=Decimal(str(round(close, 8))),
            source=source,
        )
        .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
    )
    await db.execute(stmt)


async def _onboard_price_history_br(db: AsyncSession, ticker: str, force: bool = False) -> None:
    if not force and await _has_price_history(db, ticker):
        logger.info(f"[onboarding] {ticker}: historico de precos ja existe — pulando")
        return

    rows = await fetch_price_history_full(ticker)
    if not rows:
        logger.warning(f"[onboarding] {ticker}: BRAPI range=max retornou vazio — sem historico salvo")
        return

    result = await db.execute(select(Asset).where(Asset.ticker == ticker))
    asset = result.scalar_one_or_none()
    if not asset:
        logger.warning(f"[onboarding] {ticker}: ativo nao encontrado no banco — abortando historico")
        return

    inserted = 0
    for dt, close in rows:
        ts = dt if isinstance(dt, datetime) else datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        await _upsert_price_row(db, asset.id, ts, close, source="brapi")
        inserted += 1

    latest_close = rows[-1][1]
    asset.last_price = Decimal(str(round(latest_close, 8)))
    asset.last_price_updated_at = datetime.now(timezone.utc)

    await db.commit()
    logger.info(f"[onboarding] {ticker}: {inserted} precos historicos salvos via range=max ({len(rows)} registros brutos)")


async def run_onboarding(ticker: str, asset_type: str) -> None:
    logger.info(f"[onboarding] iniciando para {ticker} ({asset_type})")

    try:
        at = AssetType(asset_type) if isinstance(asset_type, str) else asset_type
    except ValueError:
        logger.warning(f"[onboarding] asset_type invalido: {asset_type} — abortando")
        return

    if at in NO_QUOTE_TYPES:
        logger.info(
            "[onboarding] %s (%s): tipo sem cotação de mercado — pulando histórico, proventos e logo",
            ticker,
            at.value,
        )
        return

    is_intl = at in INTL_TYPES

    async with AsyncSessionLocal() as db:
        try:
            if is_intl:
                if await _has_price_history(db, ticker):
                    logger.info(f"[onboarding] {ticker}: historico intl ja existe — atualizando delta")
                n = await persist_daily_prices(db, ticker, at, days_back=_PRICE_HISTORY_DAYS_INTL, force=True)
                logger.info(f"[onboarding] {ticker}: {n} precos historicos salvos/atualizados (INTL, {_PRICE_HISTORY_DAYS_INTL}d)")
            else:
                await _onboard_price_history_br(db, ticker, force=False)
        except Exception as e:
            logger.error(f"[onboarding] {ticker}: falha ao salvar precos historicos: {e}")

        try:
            if await _has_dividends(db, ticker):
                logger.info(
                    f"[onboarding] {ticker}: proventos globais ja existem — "
                    "sincronizando eventos e vinculos da carteira"
                )
            await run_backfill(db, ticker, at)
            logger.info(f"[onboarding] {ticker}: proventos historicos sincronizados")
        except Exception as e:
            logger.error(f"[onboarding] {ticker}: falha ao sincronizar proventos: {e}")

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
