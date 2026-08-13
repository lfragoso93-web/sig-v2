"""Leituras DB-first de preços históricos para superfícies financeiras.

Este módulo não importa integrações externas nem persiste dados. Pipelines de
mercado são responsáveis por preencher ``asset_prices``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.asset_price import AssetPrice

logger = logging.getLogger(__name__)


def _parse_date_utc(date_str: str) -> datetime:
    value = date_str[:10]
    return datetime(
        int(value[:4]),
        int(value[5:7]),
        int(value[8:10]),
        tzinfo=timezone.utc,
    )


async def get_persisted_prices_at_date_batch(
    db: AsyncSession,
    tickers_with_types: list[tuple[str, AssetType]],
    target_date: str,
) -> dict[str, float]:
    """Retorna o último fechamento persistido na janela de cinco dias."""
    if not tickers_with_types:
        return {}

    ref = _parse_date_utc(target_date)
    since = ref - timedelta(days=5)
    until = ref + timedelta(hours=23, minutes=59, seconds=59)
    tickers = [ticker.upper() for ticker, _ in tickers_with_types]

    assets_result = await db.execute(
        select(Asset.id, Asset.ticker).where(Asset.ticker.in_(tickers))
    )
    asset_rows = assets_result.all()
    asset_id_to_ticker = {row.id: row.ticker.upper() for row in asset_rows}

    if not asset_id_to_ticker:
        for ticker in tickers:
            logger.warning(
                "[PersistedPrice] asset %s não encontrado no banco",
                ticker,
            )
        return {}

    rows_result = await db.execute(
        select(AssetPrice)
        .where(
            AssetPrice.asset_id.in_(asset_id_to_ticker.keys()),
            AssetPrice.timestamp >= since,
            AssetPrice.timestamp <= until,
        )
        .order_by(AssetPrice.asset_id.asc(), AssetPrice.timestamp.desc())
    )

    prices: dict[str, float] = {}
    for price_row in rows_result.scalars().all():
        ticker = asset_id_to_ticker.get(price_row.asset_id)
        if ticker and ticker not in prices:
            prices[ticker] = float(price_row.close)

    for ticker in tickers:
        if ticker not in prices:
            logger.warning(
                "[PersistedPrice] preço ausente para %s em %s",
                ticker,
                target_date,
            )

    return prices
