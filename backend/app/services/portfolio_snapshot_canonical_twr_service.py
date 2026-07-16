"""Backfill TWR usando o valuation canônico por classe de ativo."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dividend import Dividend
from app.models.transaction import Transaction
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_snapshot_twr_service import (
    _accumulated_dividends_at,
    _decimal,
    _upsert_enriched_snapshot,
    build_dividend_totals,
    calculate_transaction_components,
)
from app.services.silent_price_coverage_service import has_partial_prices_silent
from app.services.twr_service import (
    append_compounded_return_pct,
    calculate_daily_twr_pct,
)

logger = logging.getLogger(__name__)
_ZERO = Decimal("0")
_MONEY = Decimal("0.01")
_DIAGNOSTIC_PREFIXES = (
    "fixed_income_",
    "treasury_",
    "pre_listing_",
    "real_price_",
)


async def backfill_canonical_snapshots_with_returns(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int | None = None,
) -> int:
    """Reconstrói snapshots usando valuation dedicado de Renda Fixa e Tesouro."""
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return 0

    dividend_result = await db.execute(
        select(Dividend)
        .where(Dividend.portfolio_id == portfolio_id)
        .order_by(
            func.coalesce(Dividend.payment_date, Dividend.date_pagamento).asc(),
            Dividend.id.asc(),
        )
    )
    dividends_day_map, dividends_accumulated_map = build_dividend_totals(
        dividend_result.scalars().all()
    )

    start = transactions[0].date
    if days_back is not None:
        start = max(start, date.today() - timedelta(days=days_back))

    previous_value = _ZERO
    accumulated_return = _ZERO
    count = 0
    cursor = start
    today = date.today()

    while cursor <= today:
        if cursor.weekday() < 5:
            totals = await calculate_canonical_portfolio_totals(db, portfolio_id, cursor)
            realized_pnl, net_external_flow = calculate_transaction_components(
                transactions,
                cursor,
            )
            totals["realized_pnl"] = realized_pnl
            totals["total_pnl"] = (
                realized_pnl + _decimal(totals["unrealized_pnl"])
            ).quantize(_MONEY)

            dividends_day = dividends_day_map.get(cursor, _ZERO)
            dividends_accumulated = _accumulated_dividends_at(
                dividends_accumulated_map,
                cursor,
            )
            current_value = _decimal(totals["market_value"])
            daily_return = calculate_daily_twr_pct(
                previous_value,
                current_value,
                net_external_flow=net_external_flow,
                dividends_day=dividends_day,
            )
            accumulated_return = append_compounded_return_pct(
                accumulated_return,
                daily_return,
            )

            has_partial_prices = await has_partial_prices_silent(
                db,
                transactions,
                cursor,
            )
            snapshot_fields = {
                key: value
                for key, value in totals.items()
                if not key.startswith(_DIAGNOSTIC_PREFIXES)
            }
            values = {
                **snapshot_fields,
                "net_external_flow": net_external_flow,
                "dividends_day": dividends_day,
                "dividends_accumulated": dividends_accumulated,
                "daily_return_pct": daily_return,
                "accumulated_return_pct": accumulated_return,
                "has_partial_prices": has_partial_prices,
                "return_is_estimated": has_partial_prices,
            }
            await _upsert_enriched_snapshot(db, portfolio_id, cursor, values)
            previous_value = current_value
            count += 1
            if count % 30 == 0:
                await db.commit()
        cursor += timedelta(days=1)

    await db.commit()
    logger.info(
        "[snapshot_twr_canonical] portfolio=%s snapshots=%s start=%s mode=db_only",
        portfolio_id,
        count,
        start,
    )
    return count
