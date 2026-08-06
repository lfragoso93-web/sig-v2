"""Leitores DB-first para cotações cambiais persistidas."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate

USD_BRL_PAIR = "USD-BRL"


@dataclass(frozen=True, slots=True)
class PersistedFxRate:
    pair: str
    rate_date: date
    rate: Decimal


async def load_latest_fx_rate(
    db: AsyncSession,
    *,
    pair: str,
) -> PersistedFxRate | None:
    """Retorna a última cotação persistida do par, sem consultar providers."""

    result = await db.execute(
        select(FxRate)
        .where(FxRate.pair == pair)
        .order_by(FxRate.rate_date.desc(), FxRate.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return PersistedFxRate(
        pair=row.pair,
        rate_date=row.rate_date,
        rate=row.rate,
    )


async def load_latest_usd_brl_rate(db: AsyncSession) -> PersistedFxRate | None:
    """Atalho canônico para a última cotação USD/BRL persistida."""

    return await load_latest_fx_rate(db, pair=USD_BRL_PAIR)
