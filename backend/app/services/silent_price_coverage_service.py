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

    tickers = [ticker.upper() for ticker, _ in requirements]
    start = datetime.combine(target_date - timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(target_date + timedelta(days=1), datetime.max.time(), tzinfo=timezone.utc)

    assets_result = await db.execute(
        select(Asset.id, Asset.ticker).where(func.upper(Asset.ticker).in_(tickers))
    )
    asset_rows = assets_result.all()
    ticker_to_asset_id = {str(row.ticker).upper(): int(row.id) for row in asset_rows}

    covered_result = await db.execute(
        select(AssetPrice.asset_id, func.max(AssetPrice.timestamp))
        .where(
            AssetPrice.asset_id.in_(ticker_to_asset_id.values()),
            AssetPrice.timestamp >= start,
            AssetPrice.timestamp <= end,
        )
        .group_by(AssetPrice.asset_id)
    )
    covered_ids = {int(row.asset_id) for row in covered_result.all()}

    missing = [ticker for ticker in tickers if ticker_to_asset_id.get(ticker) not in covered_ids]
    if not missing:
        return False

    missing_ids = [ticker_to_asset_id[ticker] for ticker in missing if ticker in ticker_to_asset_id]
    first_dates: dict[int, date] = {}
    if missing_ids:
        first_result = await db.execute(
            select(AssetPrice.asset_id, func.min(AssetPrice.timestamp))
            .where(AssetPrice.asset_id.in_(missing_ids))
            .group_by(AssetPrice.asset_id)
        )
        for asset_id, first_timestamp in first_result.all():
            if first_timestamp is not None:
                first_dates[int(asset_id)] = first_timestamp.date()

    for ticker in missing:
        asset_id = ticker_to_asset_id.get(ticker)
        first_date = first_dates.get(asset_id) if asset_id is not None else None
        if first_date is not None and target_date < first_date:
            continue
        return True
    return False
