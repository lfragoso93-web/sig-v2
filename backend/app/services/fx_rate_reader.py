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


def _to_persisted(row: FxRate | None) -> PersistedFxRate | None:
    if row is None:
        return None
    return PersistedFxRate(
        pair=row.pair,
        rate_date=row.rate_date,
        rate=row.rate,
    )


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
    return _to_persisted(result.scalar_one_or_none())


async def load_fx_rate_at_or_before(
    db: AsyncSession,
    *,
    pair: str,
    target_date: date,
) -> PersistedFxRate | None:
    """Resolve o último fixing persistido em ou antes da data-alvo."""

    result = await db.execute(
        select(FxRate)
        .where(
            FxRate.pair == pair,
            FxRate.rate_date <= target_date,
        )
        .order_by(FxRate.rate_date.desc(), FxRate.id.desc())
        .limit(1)
    )
    return _to_persisted(result.scalar_one_or_none())


async def load_usd_brl_rate_at_or_before(
    db: AsyncSession,
    target_date: date,
) -> PersistedFxRate | None:
    """Resolve USD/BRL persistido em ou antes da data-alvo."""

    return await load_fx_rate_at_or_before(
        db,
        pair=USD_BRL_PAIR,
        target_date=target_date,
    )


async def load_usd_brl_rates_for_dates(
    db: AsyncSession,
    target_dates: list[date],
) -> dict[date, PersistedFxRate]:
    """Resolve datas distintas usando somente `fx_rates` persistida.

    A implementação é deliberadamente simples e previsível: cada data distinta
    é resolvida pelo último fixing conhecido em ou antes dela. Não existe
    provider, fallback fixo ou mutação de banco neste leitor.
    """

    resolved: dict[date, PersistedFxRate] = {}
    for target_date in sorted(set(target_dates)):
        row = await load_usd_brl_rate_at_or_before(db, target_date)
        if row is not None:
            resolved[target_date] = row
    return resolved


async def load_latest_usd_brl_rate(db: AsyncSession) -> PersistedFxRate | None:
    """Atalho canônico para a última cotação USD/BRL persistida."""

    return await load_latest_fx_rate(db, pair=USD_BRL_PAIR)
