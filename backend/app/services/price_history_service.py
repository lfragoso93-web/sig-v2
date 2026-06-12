"""
Servico de historico de precos.
Busca cotacoes diarias via BRAPI / yfinance e persiste em asset_prices.
Usado pelo scheduler (job diario) e pelo endpoint GET /prices/{ticker}/history.
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import yfinance as yf
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.brapi import fetch_quotes as brapi_fetch_quotes
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)

# Tipos que usam BRAPI para preco intraday / fechamento
BR_TYPES = {
    AssetType.ACAO, AssetType.FII, AssetType.ETF_NACIONAL,
    AssetType.TESOURO_DIRETO, AssetType.CRIPTO,
}
INTL_TYPES = {AssetType.STOCK, AssetType.ETF_INTERNACIONAL}


# ── helpers ──────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def _upsert_price(
    db: AsyncSession,
    asset_id: int,
    timestamp: datetime,
    close: float,
    source: str = "brapi",
) -> None:
    """INSERT … ON CONFLICT DO NOTHING para evitar duplicatas."""
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
        asset = Asset(
            ticker=ticker,
            name=ticker,
            asset_type=asset_type,
        )
        db.add(asset)
        await db.flush()
    return asset


async def _last_saved_ts(db: AsyncSession, asset_id: int) -> Optional[datetime]:
    result = await db.execute(
        select(func.max(AssetPrice.timestamp)).where(AssetPrice.asset_id == asset_id)
    )
    return result.scalar_one_or_none()


# ── busca historica yfinance ──────────────────────────────────────────────────

def _fetch_yf_history(ticker: str, days: int = 365) -> list[tuple[datetime, float]]:
    """
    Retorna lista de (timestamp_utc, close) para os ultimos `days` dias.
    Executa de forma sincrona — chamar dentro de run_in_executor.
    """
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=f"{days}d", interval="1d", auto_adjust=True)
        if hist.empty:
            return []
        rows = []
        for ts, row in hist.iterrows():
            close = float(row["Close"])
            if close and close > 0:
                # pandas Timestamp -> datetime utc
                dt = ts.to_pydatetime()
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                rows.append((dt, close))
        return rows
    except Exception as e:
        logger.warning(f"[PriceHistory] yfinance hist error {ticker}: {e}")
        return []


# ── API publica ───────────────────────────────────────────────────────────────

async def persist_daily_prices(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days_back: int = 365,
) -> int:
    """
    Busca historico de precos e persiste em asset_prices.
    Retorna numero de registros inseridos.
    Usa INSERT ON CONFLICT DO NOTHING — seguro para rodar multiplas vezes.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    asset = await _get_or_create_asset(db, ticker, asset_type)
    last_ts = await _last_saved_ts(db, asset.id)

    # Limita o backfill ao necessario
    if last_ts:
        delta = (_now_utc() - last_ts).days
        days_back = min(days_back, max(delta + 1, 2))

    rows: list[tuple[datetime, float]] = []

    if asset_type in INTL_TYPES:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            rows = await loop.run_in_executor(ex, _fetch_yf_history, ticker, days_back)
        source = "yfinance"
    elif asset_type in BR_TYPES:
        # BRAPI retorna cotacao atual — para historico BR usa yfinance com sufixo .SA
        yf_ticker = ticker if "." in ticker else f"{ticker}.SA"
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            rows = await loop.run_in_executor(ex, _fetch_yf_history, yf_ticker, days_back)
        source = "yfinance_br"
    else:
        # Fallback: BRAPI snapshot (so preco atual, sem historico)
        result = await brapi_fetch_quotes([ticker])
        price = result.get(ticker)
        if price:
            rows = [(_now_utc().replace(hour=18, minute=0, second=0, microsecond=0), price)]
        source = "brapi"

    inserted = 0
    for ts, close in rows:
        await _upsert_price(db, asset.id, ts, close, source)
        inserted += 1

    await db.commit()
    logger.info(f"[PriceHistory] {ticker}: {inserted} registros persistidos (source={source})")
    return inserted


async def get_price_history(
    db: AsyncSession,
    ticker: str,
    asset_type: AssetType,
    days: int = 90,
) -> list[dict]:
    """
    Retorna lista de {date, close} dos ultimos `days` dias.
    Se nao houver dados suficientes no banco, dispara persist_daily_prices primeiro.
    """
    asset_result = await db.execute(
        select(Asset).where(Asset.ticker == ticker, Asset.asset_type == asset_type)
    )
    asset = asset_result.scalar_one_or_none()

    # Backfill automatico se ativo nao encontrado ou sem dados recentes
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
        {
            "date": p.timestamp.strftime("%Y-%m-%d"),
            "close": float(p.close),
        }
        for p in prices
    ]
