from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.portfolio import Portfolio
from app.models.transaction import OperationType, Transaction
from app.schemas.dividend import DividendRead


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
) -> DividendRead | None:
    """Build the public read model without materializing a portfolio right."""
    entitlement_date = event.record_date or event.ex_date
    eligible_quantity = calculate_quantity_on_date(transactions, entitlement_date)
    if eligible_quantity <= 0:
        return None

    value_per_unit = Decimal(str(event.value_per_unit))
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


async def list_dividends(
    db: AsyncSession,
    portfolio_id: int,
    user_id: int,
) -> list[DividendRead]:
    portfolio = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )
    if not portfolio.scalar_one_or_none():
        raise ValueError("Carteira nao encontrada ou sem permissao")

    event_result = await db.execute(
        select(AssetDividend, Asset.ticker)
        .join(Asset, Asset.id == AssetDividend.asset_id)
        .order_by(AssetDividend.ex_date.desc())
    )
    event_rows = list(event_result.all())
    if not event_rows:
        return []

    tickers = {_normalize_ticker(ticker) for _, ticker in event_rows}
    transaction_result = await db.execute(
        select(Transaction).where(
            Transaction.portfolio_id == portfolio_id,
            func.upper(func.trim(Transaction.ticker)).in_(tickers),
        )
    )

    transactions_by_ticker: dict[str, list[Transaction]] = {
        ticker: [] for ticker in tickers
    }
    for transaction in transaction_result.scalars().all():
        normalized_ticker = _normalize_ticker(transaction.ticker)
        if normalized_ticker in transactions_by_ticker:
            transactions_by_ticker[normalized_ticker].append(transaction)

    projections: list[DividendRead] = []
    for event, ticker in event_rows:
        normalized_ticker = _normalize_ticker(ticker)
        projection = build_dividend_projection(
            event,
            normalized_ticker,
            portfolio_id,
            transactions_by_ticker[normalized_ticker],
        )
        if projection is not None:
            projections.append(projection)
    return projections
