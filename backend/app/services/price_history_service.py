"""
Servico de historico de precos.

Estrategia de busca (por camadas):
  L1 - banco (asset_prices): consulta primeiro; so busca externamente o delta faltante.
  L2 - BRAPI Pro (primario BR): fetch_price_history() para acoes, FIIs, ETFs, cripto.
  L3 - yfinance (fallback BR + primario INTL): usado quando BRAPI retorna vazio.

Usado pelo scheduler (job diario) e pelo endpoint GET /prices/{ticker}/history.
Tambem chamado por quotes_service ao adicionar transacao retroativa.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.asset_types import BRAPI_HISTORY_TYPES, INTL_TYPES, yf_ticker
from app.integrations.brapi import fetch_price_history as brapi_fetch_history
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

# Executor global para chamadas yfinance (nao recria a cada request)
_YF_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="yfinance_hist")

# Quantos segundos o last_price pode ficar sem atualizacao antes de ir a API
PRICE_TTL_SECONDS = 900  # 15 minutos


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def _upsert_price(
    db: AsyncSession,
    asset_id: int,
    timestamp: datetime,
    close: float,
    source: str = "brapi",
) -> None:
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


async def _get_or_create_asset(db: AsyncSession, ticker: str, asset_type: AssetType) -> Asset:
    result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        asset = Asset(ticker=ticker, name=ticker, asset_type=asset_type)
        db.add(asset)
        await db.flush()
    return asset


async def _last_saved_ts(db: AsyncSession, asset_id: int) -> Optional[datetime]:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    return result.scalar_one_or_none()


def _fetch_yf_history_sync(yf_sym: str, days: int) -> list[tuple[datetime, float]]:
    try:
        tk = yf.Ticker(yf_sym)
        hist = tk.history(period=f"{days}d", interval="1d", auto_adjust=True)
        if hist.empty:
            return []
        rows = []
        for ts, row in hist.iterrows():
            close = float(row["Close"])
            if close and close > 0:
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                rows.append((dt, close))
        return rows
    except Exception as e:
        logger.warning(f"[PriceHistory] yfinance error {yf_sym}: {e}")
        return []


async def _fetch_yf_history(ticker: str, asset_type: AssetType, days: int) -> list[tuple[datetime, float]]:
    sym = yf_ticker(ticker, asset_type)
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_YF_EXECUTOR, _fetch_yf_history_sync, sym, days)


async def persist_daily_prices(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int = 365,
) -> int:
    asset = await _get_or_create_asset(db, ticker, asset_type)
    last_ts = await _last_saved_ts(db, asset.id)

    if last_ts:
        delta = (_now_utc() - last_ts).days
        days_back = min(days_back, max(delta + 1, 2))

    date_to = _now_utc().date().isoformat()
    date_from = (_now_utc().date() - timedelta(days=days_back)).isoformat()

    rows: list[tuple[datetime, float]] = []
    source: str = "brapi"

    if asset_type in BRAPI_HISTORY_TYPES:
        rows = await brapi_fetch_history(ticker, date_from, date_to)
        source = "brapi"

        if not rows:
            logger.info(f"[PriceHistory] BRAPI vazio para {ticker} - tentando yfinance fallback")
            rows = await _fetch_yf_history(ticker, asset_type, days_back)
            source = "yfinance_br_fallback"

    elif asset_type in INTL_TYPES:
        rows = await _fetch_yf_history(ticker, asset_type, days_back)
        source = "yfinance"

    else:
        from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes
        result = await brapi_fetch_quotes([ticker])
        price = result.get(ticker)
        if price:
            ts = _now_utc().replace(hour=18, minute=0, second=0, microsecond=0)
            rows = [(ts, price)]
        source = "brapi_snapshot"

    inserted = 0
    for ts, close in rows:
        await _upsert_price(db, asset.id, ts, close, source)
        inserted += 1

    if inserted:
        latest_close = rows[-1][1] if rows else None
        if latest_close:
            asset.last_price = Decimal(str(round(latest_close, 8)))
            asset.last_price_updated_at = _now_utc()

    await db.commit()
    logger.info(f"[PriceHistory] {ticker}: {inserted} registros persistidos (source={source})")
    return inserted


async def get_price_at_date(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    target_date: str,
) -> Optional[float]:
    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()

    if asset:
        ref = datetime.fromisoformat(target_date).replace(tzinfo=timezone.utc)
        since = ref - timedelta(days=5)
        rows = await db.execute(
            select(AssetPrice)
            .where(
                AssetPrice.asset_id == asset.id,
                AssetPrice.timestamp >= since,
                AssetPrice.timestamp <= ref + timedelta(days=1),
            )
            .order_by(AssetPrice.timestamp.desc())
            .limit(1)
        )
        price_row = rows.scalar_one_or_none()
        if price_row:
            return float(price_row.close)

    days_needed = (_now_utc().date() - datetime.fromisoformat(target_date).date()).days + 6
    await persist_daily_prices(db, ticker, asset_type, days_back=days_needed)

    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()
    if not asset:
        return None

    ref = datetime.fromisoformat(target_date).replace(tzinfo=timezone.utc)
    since = ref - timedelta(days=5)
    rows = await db.execute(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id == asset.id,
            AssetPrice.timestamp >= since,
            AssetPrice.timestamp <= ref + timedelta(days=1),
        )
        .order_by(AssetPrice.timestamp.desc())
        .limit(1)
    )
    price_row = rows.scalar_one_or_none()
    return float(price_row.close) if price_row else None


async def get_price_history(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days: int = 90,
) -> list[dict]:
    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()

    if asset is None:
        await persist_daily_prices(db, ticker, asset_type, days_back=days)
        asset_result = await db.execute(
            select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
        )
        asset = asset_result.scalar_one_or_none()
        if asset is None:
            return []
    else:
        last_ts = await _last_saved_ts(db, asset.id)
        if last_ts is None or (_now_utc() - last_ts).days > 1:
            await persist_daily_prices(db, ticker, asset_type, days_back=days)

    since = _now_utc() - timedelta(days=days)
    rows_result = await db.execute(
        select(AssetPrice)
        .where(AssetPrice.asset_id == asset.id, AssetPrice.timestamp >= since)
        .order_by(AssetPrice.timestamp.asc())
    )
    prices = rows_result.scalars().all()

    return [
        {"date": p.timestamp.strftime("%Y-%m-%d"), "close": float(p.close)}
        for p in prices
    ]
