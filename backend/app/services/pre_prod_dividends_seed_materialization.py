"""Materialização transacional por carteira do seed isolado de proventos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus
from app.models.transaction import Transaction
from app.services.dividend_entitlement_service import (
    calculate_net_quantity,
    calculate_net_value,
)
from app.services.dividend_type_service import (
    CASH_DIVIDEND_TYPES,
    normalize_dividend_type,
)


class DividendsSeedMaterializationError(RuntimeError):
    """Falha bloqueante na materialização de direitos por carteira."""


@dataclass(frozen=True)
class DividendsSeedMaterializationResult:
    created: int
    updated: int
    unchanged: int
    skipped_non_cash: int

    @property
    def processed(self) -> int:
        return self.created + self.updated + self.unchanged


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _right_values(
    *,
    event: AssetDividend,
    ticker: str,
    quantity: float,
    as_of: date,
) -> dict[str, object]:
    event_type = normalize_dividend_type(event.dividend_type)
    value_per_unit = _decimal(event.value_per_unit)
    total_value = _decimal(quantity) * value_per_unit
    net_value = _decimal(calculate_net_value(event_type, float(total_value)))
    payment_date = event.payment_date
    status = (
        DividendStatus.RECEBIDO
        if payment_date is not None and payment_date <= as_of
        else DividendStatus.A_RECEBER
    )
    quantity_value = _decimal(quantity)
    return {
        "quantity": quantity_value,
        "total_value": total_value,
        "net_value": net_value,
        "status": status,
        "ticker": ticker,
        "ex_date": event.ex_date,
        "payment_date": payment_date,
        "value_per_unit": value_per_unit,
        "total_received": total_value,
        "dividend_type": event_type.value,
        "date_ex": event.ex_date,
        "date_pagamento": payment_date or event.ex_date,
        "quantity_on_date": quantity_value,
        "value_per_share": value_per_unit,
    }


async def materialize_portfolio_dividends_strict(
    *,
    db: AsyncSession,
    as_of: date,
) -> DividendsSeedMaterializationResult:
    """Materializa direitos sem ``commit`` ou ``rollback`` internos."""

    event_rows = (
        await db.execute(
            select(Asset, AssetDividend)
            .join(AssetDividend, AssetDividend.asset_id == Asset.id)
            .order_by(AssetDividend.id)
        )
    ).all()
    if not event_rows:
        return DividendsSeedMaterializationResult(0, 0, 0, 0)

    cash_events: list[tuple[Asset, AssetDividend]] = []
    skipped_non_cash = 0
    for asset, event in event_rows:
        event_type = normalize_dividend_type(event.dividend_type)
        if event_type not in CASH_DIVIDEND_TYPES:
            skipped_non_cash += 1
            continue
        if event.value_per_unit is None or _decimal(event.value_per_unit) <= 0:
            raise DividendsSeedMaterializationError(
                f"evento monetário {event.id} sem valor unitário positivo"
            )
        cash_events.append((asset, event))

    if not cash_events:
        return DividendsSeedMaterializationResult(0, 0, 0, skipped_non_cash)

    tickers = sorted({str(asset.ticker).strip().upper() for asset, _ in cash_events})
    transaction_rows = (
        await db.execute(
            select(
                Transaction.portfolio_id,
                Transaction.ticker,
                Transaction.date,
                Transaction.operation,
                Transaction.quantity,
            ).where(func.upper(Transaction.ticker).in_(tickers))
        )
    ).all()
    transactions: dict[tuple[int, str], list[tuple]] = {}
    portfolio_ids: set[int] = set()
    for portfolio_id, ticker, tx_date, operation, quantity in transaction_rows:
        normalized_ticker = str(ticker).strip().upper()
        portfolio_ids.add(portfolio_id)
        transactions.setdefault((portfolio_id, normalized_ticker), []).append(
            (tx_date, operation, quantity)
        )

    event_ids = [event.id for _, event in cash_events]
    existing_rows: list[Dividend] = []
    if portfolio_ids:
        existing_rows = (
            await db.execute(
                select(Dividend).where(
                    Dividend.portfolio_id.in_(sorted(portfolio_ids)),
                    Dividend.asset_dividend_id.in_(event_ids),
                )
            )
        ).scalars().all()

    existing: dict[tuple[int, int], Dividend] = {}
    for right in existing_rows:
        key = (right.portfolio_id, right.asset_dividend_id)
        if key in existing:
            raise DividendsSeedMaterializationError(
                "direito duplicado para "
                f"portfolio_id={key[0]}, asset_dividend_id={key[1]}"
            )
        existing[key] = right

    created = 0
    updated = 0
    unchanged = 0
    eligible_keys: set[tuple[int, int]] = set()
    for asset, event in cash_events:
        ticker = str(asset.ticker).strip().upper()
        entitlement_date = event.record_date or event.ex_date
        for portfolio_id in sorted(portfolio_ids):
            quantity = calculate_net_quantity(
                transactions.get((portfolio_id, ticker), []),
                entitlement_date,
            )
            if quantity <= 0:
                continue

            key = (portfolio_id, event.id)
            eligible_keys.add(key)
            values = _right_values(
                event=event,
                ticker=ticker,
                quantity=quantity,
                as_of=as_of,
            )
            right = existing.get(key)
            if right is None:
                db.add(
                    Dividend(
                        portfolio_id=portfolio_id,
                        asset_dividend_id=event.id,
                        **values,
                    )
                )
                created += 1
                continue

            changed = False
            for field, value in values.items():
                if getattr(right, field) != value:
                    setattr(right, field, value)
                    changed = True
            if changed:
                updated += 1
            else:
                unchanged += 1

    stale_keys = sorted(set(existing) - eligible_keys)
    if stale_keys:
        rendered = ", ".join(
            f"{portfolio_id}/{event_id}" for portfolio_id, event_id in stale_keys
        )
        raise DividendsSeedMaterializationError(
            f"direitos existentes sem elegibilidade: {rendered}"
        )

    if created or updated:
        await db.flush()
    return DividendsSeedMaterializationResult(
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped_non_cash=skipped_non_cash,
    )
