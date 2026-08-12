"""Leitura DB-first de câmbio para superfícies financeiras HTTP.

Este módulo não importa integrações externas e não persiste dados. Pipelines de
mercado continuam responsáveis por atualizar ``fx_rates``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fx_rate import FxRate

PAIR_USD_BRL = "USD-BRL"
PERSISTED_FX_FALLBACK_RATE = 5.70


async def get_persisted_usd_brl_rate(db: AsyncSession) -> float:
    """Retorna a última USD/BRL persistida até hoje, sem I/O externo ou write."""
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(FxRate.rate)
        .where(
            FxRate.pair == PAIR_USD_BRL,
            FxRate.rate_date <= today,
        )
        .order_by(FxRate.rate_date.desc())
        .limit(1)
    )
    rate = result.scalar_one_or_none()
    if rate is None:
        return PERSISTED_FX_FALLBACK_RATE
    return float(rate)
