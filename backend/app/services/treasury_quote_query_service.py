"""Leitura enriquecida de PU/taxa do Tesouro para superficies de input."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tesouro_transparente import fetch_official_treasury_quote
from app.models.asset_price import AssetPrice


async def load_treasury_rate_at_or_before(
    db: AsyncSession,
    *,
    asset_id: int,
    ticker: str,
    target_date: date,
) -> tuple[float | None, str | None]:
    """Retorna taxa persistida; usa fonte oficial como fallback ate o proximo seed."""
    rate_result = await db.execute(
        select(AssetPrice.open, AssetPrice.timestamp)
        .where(
            AssetPrice.asset_id == asset_id,
            func.date(AssetPrice.timestamp) <= target_date,
            AssetPrice.open.is_not(None),
        )
        .order_by(AssetPrice.timestamp.desc())
        .limit(1)
    )
    rate_row = rate_result.first()
    if rate_row and rate_row[0] is not None:
        timestamp = rate_row[1]
        rate_date = timestamp.date().isoformat() if isinstance(timestamp, datetime) else None
        return float(rate_row[0]), rate_date

    official_quote = await fetch_official_treasury_quote(
        ticker.lower(),
        target_date,
    )
    if official_quote is None:
        return None, None

    official_date, _official_price, official_rate = official_quote
    return official_rate, official_date.date().isoformat()
