"""Leitura DB-first de câmbio para superfícies financeiras HTTP.

Este módulo não importa integrações externas e não persiste dados. Pipelines de
mercado continuam responsáveis por atualizar ``fx_rates``.
"""
from __future__ import annotations

from datetime import date as DateType, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate

PAIR_USD_BRL = "USD-BRL"


async def get_persisted_usd_brl_rate_for_date(
    db: AsyncSession,
    target_date: DateType,
) -> float:
    """Retorna a última USD/BRL persistida até a data, sem I/O externo ou write."""
    today = datetime.now(timezone.utc).date()
    effective_date = min(target_date, today)
    result = await db.execute(
        select(FxRate.rate)
        .where(
            FxRate.pair == PAIR_USD_BRL,
            FxRate.rate_date <= effective_date,
        )
        .order_by(FxRate.rate_date.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if rate is None:
        raise RuntimeError(
            "cobertura USD-BRL persistida indisponível em ou antes de "
            f"{effective_date.isoformat()}"
        )
    return float(rate)


async def get_persisted_usd_brl_rate(db: AsyncSession) -> float:
    """Retorna a última USD/BRL persistida até hoje, sem I/O externo ou write."""
    return await get_persisted_usd_brl_rate_for_date(
        db,
        datetime.now(timezone.utc).date(),
    )
