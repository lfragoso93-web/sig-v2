"""Leitura DB-first de preços atuais persistidos para superfícies financeiras.

Este módulo não importa providers nem persiste dados. Pipelines de mercado e
refreshes explícitos são responsáveis por atualizar ``assets.last_price``.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset


async def get_persisted_current_prices(
    db: AsyncSession,
    tickers: list[str],
) -> dict[str, float]:
    """Retorna ``last_price`` persistido por ticker, sem requisito de frescor."""
    normalized = sorted({ticker.strip().upper() for ticker in tickers if ticker.strip()})
    if not normalized:
        return {}

    result = await db.execute(
        select(Asset.ticker, Asset.last_price).where(
            Asset.ticker.in_(normalized),
            Asset.last_price.is_not(None),
        )
    )
    return {
        str(row.ticker).strip().upper(): float(row.last_price)
        for row in result.all()
        if row.ticker and row.last_price is not None
    }
