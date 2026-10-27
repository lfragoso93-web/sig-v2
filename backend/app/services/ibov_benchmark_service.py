"""Serviço de sincronização diária e histórica das cotações do IBOV (Ibovespa).

Persiste fechamentos em asset_prices associados ao ativo IBOV/IBOVESPA.
Utiliza Brapi (símbolo ^BVSP) com fallback para yfinance (^BVSP).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.asset_price import AssetPrice
from app.services.b3_historical_market_rebuild_service import _ensure_ibov_benchmark_asset

logger = logging.getLogger(__name__)

_BRAPI_IBOV_SYMBOL = "^BVSP"
_YAHOO_IBOV_SYMBOL = "^BVSP"
_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


async def _fetch_ibov_brapi(range_str: str = "1mo") -> list[dict]:
    """Busca cotações do IBOV via BRAPI (^BVSP)."""
    token = settings.BRAPI_TOKEN or ""
    url = f"https://brapi.dev/api/quote/{_BRAPI_IBOV_SYMBOL}?range={range_str}&interval=1d"
    if token:
        url += f"&token={token}"

    async with httpx.AsyncClient(timeout=30.0, headers=_DEFAULT_HEADERS) as client:
        response = await client.get(url)
        if response.status_code != 200:
            logger.warning("[ibov_sync] BRAPI retornou status %s", response.status_code)
            return []
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            return []

        hist = results[0].get("historicalDataPrice") or []
        rows: list[dict] = []
        for item in hist:
            close_val = item.get("close")
            epoch = item.get("date")
            if close_val is not None and epoch is not None:
                # epoch UTC timestamp
                ts = datetime.fromtimestamp(epoch, tz=timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                rows.append({"timestamp": ts, "close": Decimal(str(close_val)), "source": "brapi_ibov"})
        return rows


def _fetch_ibov_yahoo(period: str = "1mo") -> list[dict]:
    """Fallback síncrono via yfinance (^BVSP)."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(_YAHOO_IBOV_SYMBOL)
        hist = ticker.history(period=period, interval="1d", auto_adjust=True)
        if hist.empty:
            return []
        rows: list[dict] = []
        for ts, row in hist.iterrows():
            close_val = row.get("Close")
            if close_val is not None:
                d = ts.date()
                dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
                rows.append({"timestamp": dt, "close": Decimal(str(round(close_val, 4))), "source": "yahoo_ibov"})
        return rows
    except Exception as exc:
        logger.warning("[ibov_sync] Yahoo Finance falhou: %s", exc)
        return []


async def sync_ibov_benchmark_prices(
    db: AsyncSession,
    *,
    range_str: str = "1mo",
    commit: bool = True,
) -> int:
    """Busca cotações do IBOV e persiste de forma idempotente em asset_prices."""
    asset = await _ensure_ibov_benchmark_asset(db)

    rows = await _fetch_ibov_brapi(range_str=range_str)
    if not rows:
        import asyncio
        loop = asyncio.get_running_loop()
        rows = await loop.run_in_executor(None, _fetch_ibov_yahoo, range_str)

    if not rows:
        logger.warning("[ibov_sync] Nenhuma cotação do IBOV obtida de nenhum provider")
        return 0

    inserted = 0
    latest_ts: Optional[datetime] = None
    latest_close: Optional[Decimal] = None

    for item in rows:
        ts = item["timestamp"]
        close = item["close"]
        source = item["source"]
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset.id,
                timestamp=ts,
                close=close,
                source=source,
            )
            .on_conflict_do_update(
                constraint="uq_price_asset_timestamp",
                set_={"close": close, "source": source},
            )
        )
        await db.execute(stmt)
        inserted += 1
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
            latest_close = close

    if latest_close is not None:
        asset.last_price = float(latest_close)
        asset.last_price_updated_at = latest_ts or datetime.now(timezone.utc)

    if commit:
        await db.commit()

    logger.info("[ibov_sync] Sincronização concluída: %d cotações do IBOV processadas", inserted)
    return inserted
