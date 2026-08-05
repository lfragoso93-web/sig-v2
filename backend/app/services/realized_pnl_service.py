"""Fronteira pública de runtime para ganho ou prejuízo realizado.

O runtime assíncrono usa exclusivamente a projeção canônica compartilhada. Os
calculadores puros históricos permanecem isolados no módulo de caracterização
legada e não são mais reexportados por esta fronteira operacional.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.realized_pnl_projection_reader import load_realized_pnl_by_ticker

__all__ = [
    "get_realized_pnl",
    "get_realized_pnl_by_ticker",
]


async def get_realized_pnl_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
) -> dict[str, float]:
    """Lê o resultado realizado pela projeção canônica compartilhada."""

    return await load_realized_pnl_by_ticker(db, portfolio_id)


async def get_realized_pnl(db: AsyncSession, portfolio_id: int) -> float:
    """Soma o resultado realizado canônico de todos os tickers da carteira."""

    realized = await get_realized_pnl_by_ticker(db, portfolio_id)
    return round(sum(realized.values()), 2)
