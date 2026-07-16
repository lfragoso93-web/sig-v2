"""Reparo dirigido de lacunas históricas de ativos de mercado.

Ordem de fontes:
1. BRAPI para ativos brasileiros;
2. Yahoo Finance com period=max;
3. B3 COTAHIST para ativos deslistados ou séries ainda incompletas.

O serviço é idempotente e não remove preços existentes.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.asset_types import yf_ticker
from app.core.database import AsyncSessionLocal
from app.integrations.b3_cotahist import fetch_b3_cotahist
from app.integrations.brapi import fetch_fii_historical_v2, fetch_stocks_historical_v2
from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.asset_last_price_refresh_service import refresh_asset_last_prices
from app.services.price_history_service import _run_yf_with_throttle

logger = logging.getLogger(__name__)

_DEFAULT_TICKERS = ("PETZ3", "QQQI11", "AAZQ11", "SNAG11", "AREA11")


@dataclass
class MarketGapRepairItem:
    ticker: str
    asset_type: str | None = None
    source: str | None = None
    received: int = 0
    inserted: int = 0
    transaction_start: str | None = None
    first_price: str | None = None
    error: str | None = None


@dataclass
class MarketGapRepairResult:
    requested: int = 0
    repaired: int = 0
    inserted: int = 0
    refreshed: int = 0
    errors: int = 0
    items: list[MarketGapRepairItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _fetch_yahoo_max_sync(symbol: str) -> list[tuple[datetime, float]]:
    import yfinance as yf

    history = yf.Ticker(symbol).history(period="max", interval="1d", auto_adjust=True)
    if history.empty:
        return []
    rows: list[tuple[datetime, float]] = []
    for timestamp, row in history.iterrows():
        close = row.get("Close")
        if close is None or float(close) <= 0:
            continue
        ts = timestamp.to_pydatetime()
        ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        rows.append((ts, float(close)))
    return rows


async def _fetch_provider_rows(
    ticker: str,
    asset_type: AssetType,
) -> tuple[list[tuple[datetime, float]], str]:
    rows: list[tuple[datetime, float]] = []
    source = ""
    try:
        if asset_type == AssetType.FII:
            rows = await fetch_fii_historical_v2(
                ticker=ticker,
                date_from="1900-01-01",
                date_to=datetime.now(timezone.utc).date().isoformat(),
            )
            source = "brapi_v2_fii_repair"
        else:
            rows = await fetch_stocks_historical_v2(ticker=ticker, range_="max")
            source = "brapi_v2_stocks_max_repair"
    except Exception as exc:
        logger.warning("[market_gap_repair] BRAPI falhou ticker=%s erro=%s", ticker, exc)

    symbol = yf_ticker(ticker, asset_type)
    if not rows:
        try:
            rows = await _run_yf_with_throttle(_fetch_yahoo_max_sync, symbol)
            source = "yfinance_period_max_repair"
        except Exception as exc:
            logger.warning("[market_gap_repair] Yahoo falhou ticker=%s symbol=%s erro=%s", ticker, symbol, exc)
    return rows, source


async def _persist_rows(db, asset_id: int, rows: list[tuple[datetime, float]], source: str) -> int:
    inserted_count = 0
    for timestamp, close in rows:
        if close <= 0:
            continue
        stmt = (
            pg_insert(AssetPrice)
            .values(
                asset_id=asset_id,
                timestamp=timestamp,
                close=Decimal(str(round(close, 8))),
                source=source,
            )
            .on_conflict_do_nothing(constraint="uq_price_asset_timestamp")
            .returning(AssetPrice.id)
        )
        inserted = await db.execute(stmt)
        if inserted.scalar_one_or_none() is not None:
            inserted_count += 1
    return inserted_count


async def repair_market_price_gaps(
    tickers: tuple[str, ...] | list[str] | None = None,
) -> MarketGapRepairResult:
    requested = tuple(dict.fromkeys(str(item).upper().strip() for item in (tickers or _DEFAULT_TICKERS)))
    result = MarketGapRepairResult(requested=len(requested))
    touched: set[int] = set()

    async with AsyncSessionLocal() as db:
        assets_result = await db.execute(select(Asset).where(func.upper(Asset.ticker).in_(requested)))
        assets = {str(asset.ticker).upper(): asset for asset in assets_result.scalars().all()}

        for ticker in requested:
            item = MarketGapRepairItem(ticker=ticker)
            result.items.append(item)
            asset = assets.get(ticker)
            if asset is None:
                item.error = "asset_not_found"
                result.errors += 1
                continue
            try:
                asset_type = AssetType(getattr(asset.asset_type, "value", asset.asset_type))
                item.asset_type = asset_type.value

                tx_start_result = await db.execute(
                    select(func.min(Transaction.date)).where(func.upper(Transaction.ticker) == ticker)
                )
                tx_start = tx_start_result.scalar_one_or_none()
                item.transaction_start = tx_start.isoformat() if tx_start else None
                start_year = tx_start.year if tx_start else max(datetime.now(timezone.utc).year - 10, 2000)

                rows, source = await _fetch_provider_rows(ticker, asset_type)
                inserted = await _persist_rows(db, int(asset.id), rows, source or "market_gap_repair")

                first_price_result = await db.execute(
                    select(func.min(AssetPrice.timestamp)).where(AssetPrice.asset_id == int(asset.id))
                )
                first_price = first_price_result.scalar_one_or_none()

                needs_b3 = not rows or (
                    tx_start is not None
                    and (first_price is None or first_price.date() > tx_start)
                )
                if needs_b3:
                    b3_rows = await fetch_b3_cotahist(
                        ticker,
                        start_year=max(start_year - 1, 2000),
                        end_year=datetime.now(timezone.utc).year,
                    )
                    b3_inserted = await _persist_rows(db, int(asset.id), b3_rows, "b3_cotahist")
                    if b3_rows:
                        rows = b3_rows
                        source = "b3_cotahist"
                    inserted += b3_inserted

                await db.commit()
                first_price_result = await db.execute(
                    select(func.min(AssetPrice.timestamp)).where(AssetPrice.asset_id == int(asset.id))
                )
                first_price = first_price_result.scalar_one_or_none()
                item.first_price = first_price.date().isoformat() if first_price else None
                item.source = source or None
                item.received = len(rows)
                item.inserted = inserted

                if first_price is not None:
                    touched.add(int(asset.id))
                    result.repaired += 1
                    result.inserted += inserted
                else:
                    item.error = "history_unavailable"
                    result.errors += 1
            except Exception as exc:
                await db.rollback()
                item.error = str(exc)
                result.errors += 1
                logger.exception("[market_gap_repair] erro ticker=%s", ticker)

        if touched:
            result.refreshed = await refresh_asset_last_prices(db, touched)
            await db.commit()

    logger.info(
        "[market_gap_repair] requested=%d repaired=%d inserted=%d refreshed=%d errors=%d",
        result.requested,
        result.repaired,
        result.inserted,
        result.refreshed,
        result.errors,
    )
    return result
