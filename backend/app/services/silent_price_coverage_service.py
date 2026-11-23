"""Checagem DB-only de cobertura sem duplicar logs do PriceHistory."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_price import AssetPrice
from app.models.transaction import Transaction
from app.services.lifecycle_aware_price_service import resolve_asset_ids_by_ticker_and_type
from app.services.portfolio_snapshot_twr_components import build_open_quote_requirements


async def has_partial_prices_silent(
    db: AsyncSession,
    transactions: Iterable[Transaction],
    target_date: date,
    *,
    ticker_to_asset_id_cache: dict[str, int] | None = None,
    first_dates_cache: dict[int, date | None] | None = None,
) -> bool:
    requirements = build_open_quote_requirements(transactions, target_date)
    if not requirements:
        return False

    tickers = [ticker.upper() for ticker, _ in requirements]
    start = datetime.combine(target_date - timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(target_date, datetime.max.time(), tzinfo=timezone.utc)

    if ticker_to_asset_id_cache is not None:
        missing_reqs = [
            req for req in requirements if req[0].upper() not in ticker_to_asset_id_cache
        ]
        if missing_reqs:
            _, resolved = await resolve_asset_ids_by_ticker_and_type(db, missing_reqs)
            ticker_to_asset_id_cache.update(resolved)
        ticker_to_asset_id = {
            t: ticker_to_asset_id_cache[t]
            for t in tickers
            if t in ticker_to_asset_id_cache
        }
    else:
        _, ticker_to_asset_id = await resolve_asset_ids_by_ticker_and_type(db, requirements)

    covered_ids: set[int] = set()
    if ticker_to_asset_id:
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
        if first_dates_cache is not None:
            uncached_ids = [aid for aid in missing_ids if aid not in first_dates_cache]
            if uncached_ids:
                first_result = await db.execute(
                    select(AssetPrice.asset_id, func.min(AssetPrice.timestamp))
                    .where(AssetPrice.asset_id.in_(uncached_ids))
                    .group_by(AssetPrice.asset_id)
                )
                for asset_id, first_timestamp in first_result.all():
                    first_dates_cache[int(asset_id)] = (
                        first_timestamp.date() if first_timestamp is not None else None
                    )
                for aid in uncached_ids:
                    if aid not in first_dates_cache:
                        first_dates_cache[aid] = None
            first_dates = {
                aid: first_dates_cache[aid]
                for aid in missing_ids
                if first_dates_cache.get(aid) is not None
            }
        else:
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
