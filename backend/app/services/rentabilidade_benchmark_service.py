"""Leitura DB-first dos benchmarks exibidos na página Rentabilidade."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_price import AssetPrice
from app.models.rate_history import RateHistory


_IBOV_TICKERS = {"^BVSP", "IBOV", "IBOVESPA"}


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _period_start(months: int, end_date: date) -> date | None:
    if months <= 0:
        return None
    return _month_start(end_date) - relativedelta(months=months - 1)


def _compound_percent(values: list[Decimal]) -> float:
    factor = Decimal("1")
    for value in values:
        factor *= Decimal("1") + value / Decimal("100")
    return round(float((factor - Decimal("1")) * Decimal("100")), 6)


async def _macro_monthly(
    db: AsyncSession,
    indicator: str,
    start_date: date | None,
    end_date: date,
) -> dict[str, float]:
    query = select(RateHistory).where(
        RateHistory.indicator == indicator,
        RateHistory.date <= end_date,
    )
    if start_date is not None:
        query = query.where(RateHistory.date >= start_date)
    result = await db.execute(query.order_by(RateHistory.date.asc()))

    grouped: dict[str, list[Decimal]] = defaultdict(list)
    for row in result.scalars().all():
        key = row.date.strftime("%Y-%m")
        if indicator == "CDI" and row.rate_daily is not None:
            grouped[key].append(Decimal(str(row.rate_daily)))
        elif indicator == "IPCA" and row.rate_monthly is not None:
            grouped[key] = [Decimal(str(row.rate_monthly))]

    return {key: _compound_percent(values) for key, values in grouped.items() if values}


async def _ibov_monthly(
    db: AsyncSession,
    start_date: date | None,
    end_date: date,
) -> dict[str, float]:
    asset_result = await db.execute(
        select(Asset).where(Asset.ticker.in_(_IBOV_TICKERS)).limit(1)
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        return {}

    query = select(AssetPrice).where(
        AssetPrice.asset_id == asset.id,
        AssetPrice.timestamp <= end_date,
    )
    if start_date is not None:
        query = query.where(AssetPrice.timestamp >= start_date)
    result = await db.execute(query.order_by(AssetPrice.timestamp.asc()))

    closes: dict[str, Decimal] = {}
    for row in result.scalars().all():
        closes[row.timestamp.strftime("%Y-%m")] = Decimal(str(row.close))

    returns: dict[str, float] = {}
    previous: Decimal | None = None
    for period in sorted(closes):
        current = closes[period]
        if previous not in (None, Decimal("0")):
            returns[period] = round(float((current / previous - Decimal("1")) * Decimal("100")), 6)
        previous = current
    return returns


async def get_persisted_monthly_benchmarks(
    db: AsyncSession,
    months: int = 12,
    end_date: date | None = None,
) -> dict:
    reference = end_date or date.today()
    start = _period_start(months, reference)

    cdi = await _macro_monthly(db, "CDI", start, reference)
    ipca = await _macro_monthly(db, "IPCA", start, reference)
    ibov = await _ibov_monthly(db, start, reference)
    periods = sorted(set(cdi) | set(ipca) | set(ibov))

    return {
        "source": "persisted_benchmark_history",
        "start_date": start.isoformat() if start else None,
        "end_date": reference.isoformat(),
        "availability": {
            "IBOV": {"available": bool(ibov), "status": "available" if ibov else "awaiting_persisted_history"},
            "CDI": {"available": bool(cdi), "status": "available" if cdi else "awaiting_persisted_history"},
            "IPCA": {"available": bool(ipca), "status": "available" if ipca else "awaiting_persisted_history"},
        },
        "points": [
            {
                "period": period,
                "ibov_monthly_pct": ibov.get(period),
                "cdi_monthly_pct": cdi.get(period),
                "ipca_monthly_pct": ipca.get(period),
            }
            for period in periods
        ],
    }
