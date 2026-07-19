"""Elegibilidade e reconciliação explícita de direitos a Proventos."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.asset_dividend import AssetDividend
from app.models.dividend import Dividend, DividendStatus, DividendType
from app.models.transaction import OperationType, Transaction


def calculate_net_quantity(txs: list[tuple], reference_date: date) -> float:
    """Calcula a posição líquida não negativa existente na data de referência."""
    quantity = 0.0
    for tx_date, operation, tx_quantity in txs:
        if tx_date > reference_date:
            continue
        operation_value = (
            operation.value
            if isinstance(operation, OperationType)
            else str(operation).lower()
        )
        if operation_value == OperationType.buy.value:
            quantity += float(tx_quantity)
        elif operation_value == OperationType.sell.value:
            quantity -= float(tx_quantity)
    return max(quantity, 0.0)


def _net_value(dividend_type: DividendType, total_value: float) -> float:
    return total_value * 0.85 if dividend_type == DividendType.JCP else total_value


def _dividend_type(value: DividendType | str) -> DividendType:
    if isinstance(value, DividendType):
        return value
    raw = value.value if hasattr(value, "value") else str(value or "")
    return DividendType(raw.replace("DividendType.", ""))


async def reconcile_portfolio_dividend_rights(
    db: AsyncSession,
    portfolio_id: int,
    tickers: list[str],
    *,
    commit: bool = True,
) -> int:
    """Recalcula ou remove direitos após uma mutação explícita de transações."""
    normalized_tickers = sorted({ticker.upper().strip() for ticker in tickers if ticker})
    if not normalized_tickers:
        return 0

    tx_rows = await db.execute(
        select(
            Transaction.ticker,
            Transaction.date,
            Transaction.operation,
            Transaction.quantity,
        ).where(
            Transaction.portfolio_id == portfolio_id,
            func.upper(Transaction.ticker).in_(normalized_tickers),
        )
    )
    transactions_by_ticker: dict[str, list[tuple]] = {}
    for ticker, tx_date, operation, quantity in tx_rows.all():
        transactions_by_ticker.setdefault(str(ticker).upper(), []).append(
            (tx_date, operation, quantity)
        )

    dividend_rows = await db.execute(
        select(Dividend, AssetDividend, Asset.ticker)
        .join(AssetDividend, Dividend.asset_dividend_id == AssetDividend.id)
        .join(Asset, AssetDividend.asset_id == Asset.id)
        .where(
            Dividend.portfolio_id == portfolio_id,
            func.upper(Asset.ticker).in_(normalized_tickers),
        )
    )

    changed = 0
    today = date.today()
    for dividend, event, ticker in dividend_rows.all():
        entitlement_date = event.record_date or event.ex_date
        quantity = calculate_net_quantity(
            transactions_by_ticker.get(str(ticker).upper(), []),
            entitlement_date,
        )
        if quantity <= 0:
            await db.delete(dividend)
            changed += 1
            continue

        event_type = _dividend_type(event.dividend_type)
        value_per_unit = float(event.value_per_unit or 0.0)
        total_value = quantity * value_per_unit
        net_value = _net_value(event_type, total_value)
        payment_date = event.payment_date

        dividend.quantity = Decimal(str(quantity))
        dividend.total_value = Decimal(str(total_value))
        dividend.net_value = Decimal(str(net_value))
        dividend.status = (
            DividendStatus.RECEBIDO
            if payment_date and payment_date <= today
            else DividendStatus.A_RECEBER
        )
        dividend.ticker = str(ticker).upper()
        dividend.ex_date = event.ex_date
        dividend.payment_date = payment_date
        dividend.value_per_unit = event.value_per_unit
        dividend.total_received = Decimal(str(total_value))

        dividend.date_ex = event.ex_date
        dividend.date_pagamento = payment_date or event.ex_date
        dividend.quantity_on_date = Decimal(str(quantity))
        dividend.value_per_share = event.value_per_unit
        changed += 1

    if commit:
        await db.commit()
    else:
        await db.flush()
    return changed
