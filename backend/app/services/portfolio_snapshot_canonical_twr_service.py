"""Backfill TWR usando o valuation canônico por classe de ativo."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import SYSTEM_CLOCK, Clock
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.transaction import Transaction
from app.services.canonical_dividend_aggregation_service import (
    group_received_entitlements_by_day,
)
from app.services.canonical_dividend_entitlement_reader import (
    load_portfolio_dividend_entitlements,
)
from app.services.fixed_income_valuation_service import IncompleteBenchmarkCoverageError
from app.services.portfolio_canonical_valuation_service import (
    calculate_canonical_portfolio_totals,
)
from app.services.portfolio_snapshot_twr_components import (
    accumulated_dividends_at,
    calculate_transaction_components,
    decimal_value,
    upsert_enriched_snapshot,
)
from app.services.silent_price_coverage_service import has_partial_prices_silent
from app.services.twr_service import (
    append_compounded_return_pct,
    calculate_daily_twr_pct,
)

logger = logging.getLogger(__name__)
_ZERO = Decimal("0")
_DIAGNOSTIC_PREFIXES = (
    "corporate_action_",
    "fixed_income_",
    "treasury_",
    "pre_listing_",
    "real_price_",
)
_SNAPSHOT_COLUMNS = set(PortfolioSnapshot.__table__.columns.keys())
_PERSISTED_PRICE_COVERAGE_ERROR = "cobertura persistida de preço indisponível para:"


def _is_persisted_price_gap(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    return "cobertura persistida" in message and "indispon" in message


async def backfill_canonical_snapshots_with_returns(
    db: AsyncSession,
    portfolio_id: int,
    days_back: int | None = None,
    *,
    end_date: date | None = None,
    commit: bool = True,
    clock: Clock = SYSTEM_CLOCK,
) -> int:
    """Reconstrói snapshots canônicos até ``end_date`` usando apenas dados persistidos.

    ``commit=False`` mantém todo o ciclo dentro da transação do chamador. Isso é
    usado por certificações destrutivas encapsuladas em savepoint sem criar uma
    segunda fronteira de escrita para ``PortfolioSnapshot``.
    """
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date.asc(), Transaction.id.asc())
    )
    transactions = list(tx_result.scalars().all())
    if not transactions:
        return 0

    dividends_day_map, dividends_accumulated_map = group_received_entitlements_by_day(
        await load_portfolio_dividend_entitlements(db, portfolio_id)
    )

    upper_bound = end_date or (clock.today() if clock is not SYSTEM_CLOCK else date.today())
    start = transactions[0].date

    previous_value = _ZERO
    previous_corporate_action_cash_flow_total = _ZERO
    accumulated_return = _ZERO
    count = 0
    cursor = start
    treasury_symbol_cache: dict[str, str | None] = {}
    treasury_ticker_cache: dict[str, str] = {}

    while cursor <= upper_bound:
        if cursor.weekday() < 5:
            try:
                totals = await calculate_canonical_portfolio_totals(
                    db,
                    portfolio_id,
                    cursor,
                    transactions=transactions,
                    treasury_symbol_cache=treasury_symbol_cache,
                    treasury_ticker_cache=treasury_ticker_cache,
                )
            except IncompleteBenchmarkCoverageError as exc:
                logger.warning(
                    "[snapshot_twr_canonical] portfolio=%s stop=%s reason=%s",
                    portfolio_id,
                    cursor,
                    exc,
                )
                break
            except RuntimeError as exc:
                if not _is_persisted_price_gap(exc):
                    raise
                logger.warning(
                    "[snapshot_twr_canonical] portfolio=%s skip=%s reason=%s",
                    portfolio_id,
                    cursor,
                    exc,
                )
                cursor += timedelta(days=1)
                continue
            _, net_external_flow = calculate_transaction_components(
                transactions,
                cursor,
            )
            corporate_action_cash_flow_total = decimal_value(
                totals.get("corporate_action_cash_flow_total", _ZERO)
            )
            corporate_action_cash_flow_day = (
                corporate_action_cash_flow_total
                - previous_corporate_action_cash_flow_total
            )
            if corporate_action_cash_flow_day < _ZERO:
                raise RuntimeError(
                    "fluxo acumulado de evento corporativo regrediu: "
                    f"portfolio={portfolio_id} date={cursor} "
                    f"previous={previous_corporate_action_cash_flow_total} "
                    f"current={corporate_action_cash_flow_total}"
                )

            dividends_day = dividends_day_map.get(cursor, _ZERO)
            dividends_accumulated = accumulated_dividends_at(
                dividends_accumulated_map,
                cursor,
            )
            current_value = decimal_value(totals["market_value"])
            daily_return = calculate_daily_twr_pct(
                previous_value,
                current_value,
                net_external_flow=net_external_flow,
                dividends_day=(
                    dividends_day + corporate_action_cash_flow_day
                ),
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
            treasury_unresolved = decimal_value(
                totals.get("treasury_unresolved", 0)
            ) > _ZERO
            has_partial_prices = has_partial_prices or treasury_unresolved
            snapshot_fields = {
                key: value
                for key, value in totals.items()
                if key in _SNAPSHOT_COLUMNS
                and not key.startswith(_DIAGNOSTIC_PREFIXES)
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
            await upsert_enriched_snapshot(db, portfolio_id, cursor, values)
            previous_value = current_value
            previous_corporate_action_cash_flow_total = (
                corporate_action_cash_flow_total
            )
            count += 1
            if commit and count % 30 == 0:
                await db.commit()
        cursor += timedelta(days=1)

    if commit:
        await db.commit()
    logger.info(
        "[snapshot_twr_canonical] portfolio=%s snapshots=%s start=%s end=%s mode=db_only",
        portfolio_id,
        count,
        start,
        upper_bound,
    )
    return count
