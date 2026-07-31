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
    QuantityFactorMovement,
    calculate_dividend_entitlement,
)
from app.services.corporate_position_projection_service import (
    load_eligible_quantity_actions,
)


@dataclass(frozen=True, slots=True)
class PortfolioDividendEntitlement:
    ticker: str
    asset_type: str
    event: DividendEvent
    entitlement: DividendEntitlement
    approved_on: date | None
    gross_value_per_unit: Decimal | None
    factor: Decimal | None
    complete_factor: Decimal | None
    isin_code: str | None
    asset_issued: str | None
    related_to: str | None
    remarks: str | None


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

    entitlement_dates = [
        row.record_date or row.ex_date
        for row, _asset in event_rows
        if row.record_date or row.ex_date
    ]
    actions_by_ticker = (
        await load_eligible_quantity_actions(
            db,
            tickers=[asset.ticker for _event, asset in event_rows],
            through_date=max(entitlement_dates),
        )
        if entitlement_dates
        else {}
    )

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
                asset_type=_enum_value(asset.asset_type),
                event=event,
                entitlement=calculate_dividend_entitlement(
                    event,
                    movements_by_asset.get(key, ()),
                    tuple(
                        QuantityFactorMovement(
                            effective_date=action.effective_date,
                            quantity_factor=action.quantity_factor,
                            event_id=action.event_id,
                        )
                        for action in actions_by_ticker.get(asset.ticker.upper(), ())
                    ),
                ),
                approved_on=asset_dividend.approved_on,
                gross_value_per_unit=_optional_decimal(
                    asset_dividend.gross_value_per_unit
                ),
                factor=_optional_decimal(asset_dividend.factor),
                complete_factor=_optional_decimal(asset_dividend.complete_factor),
                isin_code=asset_dividend.isin_code,
                asset_issued=asset_dividend.asset_issued,
                related_to=asset_dividend.related_to,
                remarks=asset_dividend.remarks,
            )
        )
    return results


def _enum_value(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw)


def _optional_decimal(value: object | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))
