"""
Serviço de benchmarks macroeconômicos para Renda Fixa.

- Persiste séries históricas do SGS/BCB em rate_history.
- Atualiza incrementalmente via scheduler.
- Fornece fatores acumulados para valuation de Renda Fixa.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable, Optional

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bcb_sgs import SGS_INDICATORS, fetch_many_sgs_series
from app.models.rate_history import RateHistory

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_START = date(2010, 1, 1)


def _to_decimal(value: object, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return Decimal(default)


def _daily_rate_from_annual_pct(annual_pct: Decimal) -> Decimal:
    annual = float(annual_pct / Decimal("100"))
    daily = (1.0 + annual) ** (1 / 252) - 1
    return Decimal(str(daily * 100))


async def _upsert_rate_rows(db: AsyncSession, rows: list[dict]) -> int:
    inserted_or_updated = 0
    for row in rows:
        values = {
            "indicator": row["indicator"],
            "date": row["date"],
            "source": row.get("source", "BCB_SGS"),
        }
        if row["value_field"] == "rate_daily":
            values["rate_daily"] = row["value"]
            values["rate_monthly"] = None
        else:
            values["rate_daily"] = None
            values["rate_monthly"] = row["value"]

        stmt = (
            pg_insert(RateHistory)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_rate_history_indicator_date",
                set_={
                    "rate_daily": values.get("rate_daily"),
                    "rate_monthly": values.get("rate_monthly"),
                    "source": values["source"],
                },
            )
        )
        await db.execute(stmt)
        inserted_or_updated += 1
    return inserted_or_updated


async def import_benchmark_history(
    db: AsyncSession,
    indicators: Optional[Iterable[str]] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit_last: Optional[int] = None,
    commit: bool = True,
) -> dict[str, int]:
    """Importa séries SGS/BCB para rate_history."""
    selected = [i.upper() for i in (indicators or SGS_INDICATORS.keys())]
    series = await fetch_many_sgs_series(
        indicators=selected,
        start_date=start_date,
        end_date=end_date,
        limit_last=limit_last,
    )

    stats: dict[str, int] = {}
    for indicator, rows in series.items():
        stats[indicator] = await _upsert_rate_rows(db, rows)

    if commit:
        await db.commit()
    logger.info("[benchmarks] importação BCB concluída: %s", stats)
    return stats


async def import_missing_benchmark_history(
    db: AsyncSession,
    start_date: date = DEFAULT_HISTORY_START,
    end_date: Optional[date] = None,
) -> dict[str, int]:
    """
    Backfill inicial: se a tabela estiver vazia para algum indicador, importa
    histórico desde start_date. Se já houver dados, atualiza apenas últimos 10 dias.
    """
    today = end_date or date.today()
    stats: dict[str, int] = {}

    for indicator in SGS_INDICATORS.keys():
        count_result = await db.execute(
            select(func.count()).select_from(RateHistory).where(RateHistory.indicator == indicator)
        )
        count = count_result.scalar_one() or 0
        if count == 0:
            partial = await import_benchmark_history(
                db,
                indicators=[indicator],
                start_date=start_date,
                end_date=today,
                commit=False,
            )
        else:
            partial = await import_benchmark_history(
                db,
                indicators=[indicator],
                start_date=today - timedelta(days=10),
                end_date=today,
                commit=False,
            )
        stats.update(partial)

    await db.commit()
    logger.info("[benchmarks] backfill/incremental concluído: %s", stats)
    return stats


async def get_rate_rows(
    db: AsyncSession,
    indicator: str,
    start_date: date,
    end_date: date,
) -> list[RateHistory]:
    result = await db.execute(
        select(RateHistory)
        .where(
            RateHistory.indicator == indicator.upper(),
            RateHistory.date >= start_date,
            RateHistory.date <= end_date,
        )
        .order_by(RateHistory.date.asc())
    )
    return list(result.scalars().all())


async def latest_rate(db: AsyncSession, indicator: str) -> Optional[RateHistory]:
    result = await db.execute(
        select(RateHistory)
        .where(RateHistory.indicator == indicator.upper())
        .order_by(RateHistory.date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def benchmark_factor(
    db: AsyncSession,
    indicator: str,
    start_date: date,
    end_date: date,
    multiplier_pct: Decimal = Decimal("100"),
    spread_annual_pct: Decimal = Decimal("0"),
) -> Decimal:
    """
    Retorna fator acumulado entre start_date e end_date.

    CDI/SELIC: usa taxa diária em % a.d. e aplica multiplier_pct.
    IPCA/IGPM: usa taxa mensal em % a.m. e soma spread anual por dias corridos.
    """
    indicator = indicator.upper()
    if end_date <= start_date:
        return Decimal("1")

    rows = await get_rate_rows(db, indicator, start_date, end_date)
    factor = Decimal("1")

    if indicator in {"CDI", "SELIC"}:
        for row in rows:
            daily = _to_decimal(row.rate_daily)
            effective_daily = daily * multiplier_pct / Decimal("100")
            factor *= Decimal("1") + (effective_daily / Decimal("100"))
        return factor

    if indicator in {"IPCA", "IGPM"}:
        for row in rows:
            monthly = _to_decimal(row.rate_monthly)
            factor *= Decimal("1") + (monthly / Decimal("100"))

        if spread_annual_pct:
            days = Decimal(str(max((end_date - start_date).days, 0)))
            spread_daily_pct = _daily_rate_from_annual_pct(spread_annual_pct)
            spread_factor = (Decimal("1") + spread_daily_pct / Decimal("100")) ** int(days)
            factor *= spread_factor
        return factor

    return factor


async def latest_annual_reference_pct(db: AsyncSession, indicator: str, fallback: Decimal) -> Decimal:
    """
    Compatibilidade para telas/relatórios que ainda esperam uma taxa anual.
    CDI/SELIC anualiza a última taxa diária por 252 dias úteis.
    IPCA/IGPM anualiza a última taxa mensal por 12 meses.
    """
    row = await latest_rate(db, indicator)
    if not row:
        return fallback

    if row.rate_daily is not None:
        daily = _to_decimal(row.rate_daily) / Decimal("100")
        annual = (Decimal("1") + daily) ** 252 - Decimal("1")
        return annual * Decimal("100")

    if row.rate_monthly is not None:
        monthly = _to_decimal(row.rate_monthly) / Decimal("100")
        annual = (Decimal("1") + monthly) ** 12 - Decimal("1")
        return annual * Decimal("100")

    return fallback
