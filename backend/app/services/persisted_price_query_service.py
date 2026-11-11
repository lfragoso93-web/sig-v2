"""Leituras DB-first de preços históricos para superfícies financeiras.

Este módulo não importa integrações externas nem persiste dados. Pipelines de
mercado são responsáveis por preencher ``asset_prices``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_safety import sanitize_log_value
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
    requested: dict[str, str] = {}
    requested_types: dict[str, set[str]] = {}
    for ticker, raw_type in tickers_with_types:
        cleaned = ticker.strip()
        if not cleaned:
            continue
        upper_ticker = cleaned.upper()
        requested[upper_ticker] = cleaned.lower()
        normalized_type = (
            raw_type.value if isinstance(raw_type, AssetType) else str(raw_type)
        ).strip().upper()
        if normalized_type:
            requested_types.setdefault(upper_ticker, set()).add(normalized_type)
    tickers = list(requested.keys())

    assets_result = await db.execute(
        select(Asset.id, Asset.ticker, Asset.asset_type).where(
            func.lower(Asset.ticker).in_(set(requested.values()))
        )
    )
    asset_rows = assets_result.all()
    exact_matches: dict[int, str] = {}
    fallback_matches: dict[int, str] = {}
    exact_tickers: set[str] = set()
    for row in asset_rows:
        row_ticker_upper = str(row.ticker).strip().upper()
        if row_ticker_upper not in requested:
            continue
        row_type = getattr(row, "asset_type", None)
        expected_types = requested_types.get(row_ticker_upper, set())
        if row_type is None or not expected_types or str(row_type).strip().upper() in expected_types:
            exact_matches[row.id] = row_ticker_upper
            exact_tickers.add(row_ticker_upper)
        else:
            fallback_matches[row.id] = row_ticker_upper

    asset_id_to_ticker: dict[int, str] = dict(exact_matches)
    for asset_id, row_ticker_upper in fallback_matches.items():
        if row_ticker_upper not in exact_tickers:
            asset_id_to_ticker[asset_id] = row_ticker_upper

    if not asset_id_to_ticker:
        for ticker in tickers:
            logger.warning(
                "[PersistedPrice] asset %s não encontrado no banco",
                sanitize_log_value(ticker),
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
                sanitize_log_value(ticker),
                sanitize_log_value(target_date),
            )

    return prices


async def get_persisted_price_history(
    db: AsyncSession,
    ticker: str,
    *,
    days: int = 365,
    asset_type: AssetType | str | None = None,
) -> list[dict[str, str | float]]:
    """Retorna a série persistida no contrato público ``date``/``price``."""
    normalized = ticker.strip().lower()
    if not normalized:
        return []

    query = select(Asset.id).where(func.lower(Asset.ticker) == normalized)
    if asset_type is not None:
        normalized_type = (
            asset_type.value if isinstance(asset_type, AssetType) else str(asset_type)
        ).strip()
        if normalized_type:
            query = query.where(Asset.asset_type == normalized_type)
    asset_result = await db.execute(query.order_by(Asset.id.asc()))
    scalars_fn = getattr(asset_result, "scalars", None)
    if callable(scalars_fn):
        asset_id = scalars_fn().first()
    else:
        asset_id = asset_result.scalar_one_or_none()
    if asset_id is None:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows_result = await db.execute(
        select(AssetPrice.timestamp, AssetPrice.close)
        .where(
            AssetPrice.asset_id == asset_id,
            AssetPrice.timestamp >= cutoff,
        )
        .order_by(AssetPrice.timestamp.asc())
    )
    return [
        {
            "date": row.timestamp.date().isoformat(),
            "price": float(row.close),
        }
        for row in rows_result.all()
    ]
