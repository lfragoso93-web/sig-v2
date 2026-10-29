from collections.abc import Iterable
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access_context import PortfolioAccessContext
from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.transaction import OperationType, Transaction
from app.repositories.portfolio_access_repository import get_accessible_portfolio
from app.schemas.dividend import DividendRead
from app.services.canonical_dividend_entitlement_reader import (
    load_usd_brl_rates,
    lookup_fx_rate_on_or_before,
)


READ_PORTFOLIO_DIVIDENDS = "portfolio:dividends:read"


def _normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def calculate_quantity_on_date(
    transactions: Iterable[Transaction],
    entitlement_date: date,
) -> Decimal:
    """Calculate the non-negative historical position on an entitlement date."""
    quantity = Decimal(0)
    for transaction in transactions:
        if transaction.date > entitlement_date:
            continue
        transaction_quantity = Decimal(str(transaction.quantity))
        operation = getattr(transaction.operation, "value", transaction.operation)
        if operation == OperationType.buy.value:
            quantity += transaction_quantity
        elif operation == OperationType.sell.value:
            quantity -= transaction_quantity
    return max(quantity, Decimal(0))


def build_dividend_projection(
    event: AssetDividend,
    ticker: str,
    portfolio_id: int,
    transactions: Iterable[Transaction],
    fx_rate: Decimal = Decimal(1),
) -> DividendRead | None:
    """Build the public read model without materializing a portfolio right."""
    entitlement_date = event.record_date or event.ex_date
    eligible_quantity = calculate_quantity_on_date(transactions, entitlement_date)
    if eligible_quantity <= 0:
        return None

    value_per_unit = (Decimal(str(event.value_per_unit)) * fx_rate).quantize(
        Decimal("0.00000001"),
        rounding=ROUND_HALF_UP,
    )
    dividend_type: Any = getattr(event.dividend_type, "value", event.dividend_type)
    return DividendRead(
        id=event.id,
        ticker=_normalize_ticker(ticker),
        ex_date=event.ex_date,
        payment_date=event.payment_date,
        value_per_unit=value_per_unit,
        dividend_type=dividend_type,
        total_received=eligible_quantity * value_per_unit,
        portfolio_id=portfolio_id,
    )


def _unpack_event_row(row: Any) -> tuple[AssetDividend, str, str]:
    if len(row) >= 3:
        event, ticker, currency = row[0], row[1], row[2]
    else:
        event, ticker = row[0], row[1]
        currency = getattr(event, "currency", "BRL") or "BRL"
    return event, str(ticker), str(currency or "BRL").strip().upper()


async def list_dividends(
    db: AsyncSession,
    access: PortfolioAccessContext,
) -> list[DividendRead]:
    await get_accessible_portfolio(
        db,
        access,
        required_permission=READ_PORTFOLIO_DIVIDENDS,
    )
    portfolio_id = access.portfolio_id

    event_result = await db.execute(
        select(AssetDividend, Asset.ticker, Asset.currency)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .order_by(AssetDividend.ex_date.desc())
    )
    raw_rows = list(event_result.all())
    if not raw_rows:
        return []

    unpacked_rows = [_unpack_event_row(row) for row in raw_rows]
    tickers = {_normalize_ticker(ticker) for _, ticker, _ in unpacked_rows}
    transaction_result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            func.upper(func.trim(Transaction.ticker)).in_(tickers),
        )
    )

    usd_ref_dates = [
        event.payment_date or event.ex_date
        for event, _, currency in unpacked_rows
        if currency == "USD"
    ]
    fx_dates: list[date] = []
    fx_rates: list[Decimal] = []
    if usd_ref_dates:
        fx_dates, fx_rates = await load_usd_brl_rates(db, max(usd_ref_dates))

    transactions_by_ticker: dict[str, list[Transaction]] = {
        ticker: [] for ticker in tickers
    }
    for transaction in transaction_result.scalars().all():
        normalized_ticker = _normalize_ticker(transaction.ticker)
        if normalized_ticker in transactions_by_ticker:
            transactions_by_ticker[normalized_ticker].append(transaction)

    projections: list[DividendRead] = []
    for event, ticker, currency in unpacked_rows:
        normalized_ticker = _normalize_ticker(ticker)
        fx_rate = Decimal(1)
        if currency == "USD":
            ref_date = event.payment_date or event.ex_date
            resolved_fx = lookup_fx_rate_on_or_before(fx_dates, fx_rates, ref_date)
            if resolved_fx is not None:
                fx_rate = resolved_fx
        projection = build_dividend_projection(
            event,
            normalized_ticker,
            portfolio_id,
            transactions_by_ticker[normalized_ticker],
            fx_rate=fx_rate,
        )
        if projection is not None:
            projections.append(projection)
    return projections
