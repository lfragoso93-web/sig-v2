"""Checagem DB-only de cobertura sem duplicar logs do PriceHistory."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.portfolio_snapshot_twr_service import build_open_quote_requirements


async def has_partial_prices_silent(
    db: AsyncSession,
    transactions: Iterable[Transaction],
    target_date: date,
) -> bool:
    requirements = build_open_quote_requirements(transactions, target_date)
    if not requirements:
        return False

    tickers = [ticker for ticker, _ in requirements]
    start = datetime.combine(target_date - timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(target_date + timedelta(days=1), datetime.max.time(), tzinfo=timezone.utc)

    result = await db.execute(
        select(Asset.ticker, func.max(AssetPrice.timestamp))
        .join(AssetPrice, AssetPrice.asset_id == Asset.id)
        .where(
            Asset.ticker.in_(tickers),
            AssetPrice.timestamp >= start,
            AssetPrice.timestamp <= end,
        )
        .group_by(Asset.ticker)
    )
    covered = {str(row.ticker).upper() for row in result.all()}
    return any(ticker.upper() not in covered for ticker in tickers)
