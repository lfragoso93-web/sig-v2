"""Read-only ORM adapter for canonical portfolio dividend entitlements."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.transaction import Transaction
from app.services.canonical_dividend_entitlement import (
    DividendEntitlement,
    DividendEvent,
    PositionMovement,
    calculate_dividend_entitlement,
)


@dataclass(frozen=True, slots=True)
class PortfolioDividendEntitlement:
    ticker: str
    asset_type: str
    event: DividendEvent
    entitlement: DividendEntitlement


async def load_portfolio_dividend_entitlements(
    db: AsyncSession,
    portfolio_id: int,
    *,
    ex_date_from: date | None = None,
    ex_date_to: date | None = None,
) -> list[PortfolioDividendEntitlement]:
    """Load global events and derive rights without persisting portfolio rows."""
    events_stmt = (
        select(AssetDividend, Asset)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .join(
            Transaction,
            and_(
                Transaction.ticker == Asset.ticker,
                Transaction.asset_type == Asset.asset_type,
            ),
        )
        .where(Transaction.portfolio_id == portfolio_id)
        .distinct()
        .order_by(AssetDividend.ex_date, AssetDividend.id)
    )
    if ex_date_from is not None:
        events_stmt = events_stmt.where(AssetDividend.ex_date >= ex_date_from)
    if ex_date_to is not None:
        events_stmt = events_stmt.where(AssetDividend.ex_date <= ex_date_to)

    event_rows = (await db.execute(events_stmt)).all()
    if not event_rows:
        return []

    movements_stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.date, Transaction.id)
    )
    transactions = (await db.execute(movements_stmt)).scalars().all()

    movements_by_asset: dict[tuple[str, str], list[PositionMovement]] = {}
    for transaction in transactions:
        key = (transaction.ticker, transaction.asset_type)
        movements_by_asset.setdefault(key, []).append(
            PositionMovement(
                transaction_date=transaction.date,
                operation=_enum_value(transaction.operation),
                quantity=Decimal(str(transaction.quantity)),
            )
        )

    results: list[PortfolioDividendEntitlement] = []
    for asset_dividend, asset in event_rows:
        currency = str(asset.currency or "").strip()
        if not currency:
            raise ValueError(f"asset {asset.ticker} has no currency")
        event = DividendEvent(
            event_id=asset_dividend.id,
            record_date=asset_dividend.record_date,
            ex_date=asset_dividend.ex_date,
            payment_date=asset_dividend.payment_date,
            event_type=_enum_value(asset_dividend.dividend_type),
            value_per_unit=Decimal(str(asset_dividend.value_per_unit)),
            currency=currency,
        )
        key = (asset.ticker, asset.asset_type)
        results.append(
            PortfolioDividendEntitlement(
                ticker=asset.ticker,
                asset_type=asset.asset_type,
                event=event,
                entitlement=calculate_dividend_entitlement(
                    event,
                    movements_by_asset.get(key, ()),
                ),
            )
        )
    return results


def _enum_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)
