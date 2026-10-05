"""Leitura DB-first de preços atuais persistidos para superfícies financeiras.

Este módulo não importa providers nem persiste dados. Pipelines de mercado e
refreshes explícitos são responsáveis por atualizar ``assets.last_price``.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


async def get_persisted_current_prices(
    db: AsyncSession,
    tickers: list[str],
) -> dict[str, float]:
    """Retorna ``last_price`` persistido por ticker, sem requisito de frescor."""
    requested = {
        ticker.strip().upper(): ticker.strip().lower()
        for ticker in tickers
        if ticker.strip()
    }
    if not requested:
        return {}

    result = await db.execute(
        select(Asset.ticker, Asset.last_price).where(
            func.lower(Asset.ticker).in_(set(requested.values())),
            Asset.last_price.is_not(None),
        )
    )
    prices_by_lower = {
        str(row.ticker).strip().lower(): float(row.last_price)
        for row in result.all()
        if row.ticker and row.last_price is not None
    }
    return {
        requested_ticker: prices_by_lower[lookup_key]
        for requested_ticker, lookup_key in requested.items()
        if lookup_key in prices_by_lower
    }
