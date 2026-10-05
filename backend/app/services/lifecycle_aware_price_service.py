"""Lookup de precos consciente do ciclo de negociacao do ativo.

Datas anteriores ao primeiro preco oficial sao tratadas como PRE_LISTING e nao
como falha de cobertura. O chamador pode usar o custo medio da posicao como
valor contabil durante esse periodo de subscricao/pre-negociacao.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)
_MAX_STALE_MARKET_PRICE_DAYS = 90


def _is_stale_price_usable(
    *,
    last_price_date: date | None,
    target_date: date,
    max_age_days: int = _MAX_STALE_MARKET_PRICE_DAYS,
) -> bool:
    if last_price_date is None or last_price_date > target_date:
        return False
    return (target_date - last_price_date).days <= max_age_days


async def get_prices_at_date_with_lifecycle(
    db: AsyncSession,
    tickers_with_types: list[tuple[str, AssetType]],
    target_date: date,
) -> tuple[dict[str, float], set[str], set[str]]:
    """Retorna precos, tickers PRE_LISTING e lacunas reais.

    A busca de preco preserva a janela operacional de cinco dias usada pelo
    PriceHistory. Quando nao existe preco nessa janela, consultamos a primeira
    cotacao oficial do ativo:

    - target_date < first_price_date: PRE_LISTING, sem warning;
    - target_date >= first_price_date: REAL_GAP, com warning;
    - ativo sem historico: REAL_GAP, com warning.
    """
    if not tickers_with_types:
        return {}, set(), set()

    tickers = list(dict.fromkeys(ticker.upper() for ticker, _ in tickers_with_types))
    start = datetime.combine(target_date - timedelta(days=5), datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(target_date + timedelta(days=1), datetime.max.time(), tzinfo=timezone.utc)

    assets_result = await db.execute(
        select(Asset.id, Asset.ticker).where(func.upper(Asset.ticker).in_(tickers))
    )
    asset_rows = assets_result.all()
    asset_id_to_ticker = {int(row.id): str(row.ticker).upper() for row in asset_rows}
    ticker_to_asset_id = {ticker: asset_id for asset_id, ticker in asset_id_to_ticker.items()}

    prices: dict[str, float] = {}
    if asset_id_to_ticker:
        rows_result = await db.execute(
            select(AssetPrice)
            .where(
                AssetPrice.asset_id.in_(asset_id_to_ticker.keys()),
                AssetPrice.timestamp >= start,
                AssetPrice.timestamp <= end,
            )
            .order_by(AssetPrice.asset_id.asc(), AssetPrice.timestamp.desc())
        )
        for row in rows_result.scalars().all():
            ticker = asset_id_to_ticker.get(int(row.asset_id))
            if ticker and ticker not in prices:
                prices[ticker] = float(row.close)

    missing = [ticker for ticker in tickers if ticker not in prices]
    pre_listing: set[str] = set()
    real_gaps: set[str] = set()
    if not missing:
        return prices, pre_listing, real_gaps

    missing_ids = [ticker_to_asset_id[ticker] for ticker in missing if ticker in ticker_to_asset_id]
    first_dates: dict[int, date] = {}
    last_prices: dict[int, tuple[date, float]] = {}
    if missing_ids:
        first_result = await db.execute(
            select(AssetPrice.asset_id, func.min(AssetPrice.timestamp))
            .where(AssetPrice.asset_id.in_(missing_ids))
            .group_by(AssetPrice.asset_id)
        )
        for asset_id, first_timestamp in first_result.all():
            if first_timestamp is not None:
                first_dates[int(asset_id)] = first_timestamp.date()

        stale_start = datetime.combine(
            target_date - timedelta(days=_MAX_STALE_MARKET_PRICE_DAYS),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        stale_end = datetime.combine(
            target_date,
            datetime.max.time(),
            tzinfo=timezone.utc,
        )
        stale_result = await db.execute(
            select(AssetPrice)
            .where(
                AssetPrice.asset_id.in_(missing_ids),
                AssetPrice.timestamp >= stale_start,
                AssetPrice.timestamp <= stale_end,
            )
            .order_by(AssetPrice.asset_id.asc(), AssetPrice.timestamp.desc())
        )
        for row in stale_result.scalars().all():
            asset_id = int(row.asset_id)
            if asset_id not in last_prices:
                last_prices[asset_id] = (row.timestamp.date(), float(row.close))

    for ticker in missing:
        asset_id = ticker_to_asset_id.get(ticker)
        first_date = first_dates.get(asset_id) if asset_id is not None else None
        if first_date is not None and target_date < first_date:
            pre_listing.add(ticker)
            continue
        if asset_id is not None:
            stale = last_prices.get(asset_id)
            if stale and _is_stale_price_usable(
                last_price_date=stale[0],
                target_date=target_date,
            ):
                prices[ticker] = stale[1]
                continue
        real_gaps.add(ticker)
        logger.warning(
            "[PriceLifecycle] lacuna real de preco para %s em %s first_price=%s",
            ticker,
            target_date,
            first_date,
        )

    return prices, pre_listing, real_gaps
