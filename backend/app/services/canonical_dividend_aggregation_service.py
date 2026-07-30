"""Read-only aggregation of canonical portfolio dividend entitlements."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.canonical_dividend_entitlement import EntitlementReason
from app.services.canonical_dividend_entitlement_reader import (
    PortfolioDividendEntitlement,
    load_portfolio_dividend_entitlements,
)

_ZERO = Decimal("0")
_MONEY_STEP = Decimal("0.01")


def aggregate_received_entitlements(
    items: Iterable[PortfolioDividendEntitlement],
    *,
    cutoff: date | None = None,
    as_of: date,
    tickers: Iterable[str] | None = None,
) -> Decimal:
    """Sum eligible BRL cash rights paid inside the requested interval."""
    normalized_tickers = (
        {ticker.upper() for ticker in tickers if ticker}
        if tickers is not None
        else None
    )
    total = _ZERO
    for item in items:
        payment_date = item.event.payment_date
        if item.entitlement.reason is not EntitlementReason.ELIGIBLE:
            continue
        if item.entitlement.currency.upper() != "BRL":
            continue
        if payment_date is None or payment_date > as_of:
            continue
        if cutoff is not None and payment_date < cutoff:
            continue
        if normalized_tickers is not None and item.ticker.upper() not in normalized_tickers:
            continue
        total += item.entitlement.net_amount
    return total.quantize(_MONEY_STEP, rounding=ROUND_HALF_UP)


async def load_received_entitlement_totals(
    db: AsyncSession,
    portfolio_id: int,
    *,
    cutoff: date,
    as_of: date,
) -> tuple[float, float]:
    """Load rights once and return received totals for the cutoff and all time."""
    items = await load_portfolio_dividend_entitlements(db, portfolio_id)
    total = aggregate_received_entitlements(items, as_of=as_of)
    total_from_cutoff = aggregate_received_entitlements(
        items,
        cutoff=cutoff,
        as_of=as_of,
    )
    return float(total_from_cutoff), float(total)


async def load_received_entitlements_by_ticker(
    db: AsyncSession,
    portfolio_id: int,
    tickers: Iterable[str],
    *,
    as_of: date,
) -> dict[str, float]:
    """Load rights once and group received BRL amounts by requested ticker."""
    normalized = sorted({ticker.upper() for ticker in tickers if ticker})
    if not normalized:
        return {}

    items = await load_portfolio_dividend_entitlements(db, portfolio_id)
    return {
        ticker: float(
            aggregate_received_entitlements(
                items,
                as_of=as_of,
                tickers=(ticker,),
            )
        )
        for ticker in normalized
    }
