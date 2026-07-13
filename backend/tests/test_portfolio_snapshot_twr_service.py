from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

from app.models.dividend import Dividend, DividendStatus
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_snapshot_twr_service import (
    build_dividend_totals,
    calculate_transaction_components,
)


def _tx(
    *,
    operation: OperationType,
    quantity: float,
    price: float,
    tx_date: date,
    fees: float = 0,
    ticker: str = "TEST3",
    notes: str | None = None,
) -> Transaction:
    return cast(
        Transaction,
        SimpleNamespace(
            operation=operation,
            quantity=quantity,
            price=price,
            fees=fees,
            date=tx_date,
            ticker=ticker,
            fx_rate=None,
            notes=notes,
        ),
    )


def _dividend(
    *,
    payment_date: date | None,
    value: float,
    status: DividendStatus = DividendStatus.RECEBIDO,
    dividend_type: str = "DIVIDENDO",
    legacy_payment_date: date | None = None,
) -> Dividend:
    return cast(
        Dividend,
        SimpleNamespace(
            status=status,
            dividend_type=dividend_type,
            payment_date=payment_date,
            date_pagamento=legacy_payment_date,
            net_value=Decimal(str(value)),
            total_received=None,
            total_value=None,
        ),
    )


def test_buy_is_inferred_as_positive_external_flow() -> None:
    tx_date = date(2026, 1, 5)
    realized, flow = calculate_transaction_components(
        [
            _tx(
                operation=OperationType.buy,
                quantity=10,
                price=20,
                fees=2,
                tx_date=tx_date,
            )
        ],
        tx_date,
    )

    assert realized == Decimal("0.00")
    assert flow == Decimal("202.00")


def test_sell_fee_reduces_withdrawal_and_realized_profit() -> None:
    buy_date = date(2026, 1, 5)
    sell_date = date(2026, 1, 6)
    realized, flow = calculate_transaction_components(
        [
            _tx(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=buy_date,
            ),
            _tx(
                operation=OperationType.sell,
                quantity=4,
                price=15,
                fees=2,
                tx_date=sell_date,
            ),
        ],
        sell_date,
    )

    assert realized == Decimal("18.00")
    assert flow == Decimal("-58.00")


def test_closed_position_preserves_realized_loss() -> None:
    buy_date = date(2026, 1, 5)
    sell_date = date(2026, 1, 6)
    realized, flow = calculate_transaction_components(
        [
            _tx(
                operation=OperationType.buy,
                quantity=5,
                price=20,
                tx_date=buy_date,
            ),
            _tx(
                operation=OperationType.sell,
                quantity=5,
                price=18,
                fees=1,
                tx_date=sell_date,
            ),
        ],
        sell_date,
    )

    assert realized == Decimal("-11.00")
    assert flow == Decimal("-89.00")


def test_technical_ticker_change_does_not_create_external_flow() -> None:
    event_date = date(2026, 1, 6)
    marker = "Evento corporativo - troca de ticker #7"
    realized, flow = calculate_transaction_components(
        [
            _tx(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2026, 1, 5),
                ticker="OLD3",
            ),
            _tx(
                operation=OperationType.sell,
                quantity=10,
                price=10,
                tx_date=event_date,
                ticker="OLD3",
                notes=marker,
            ),
            _tx(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=event_date,
                ticker="NEW3",
                notes=marker,
            ),
        ],
        event_date,
    )

    assert realized == Decimal("0.00")
    assert flow == Decimal("0.00")


def test_dividends_use_payment_date_and_ignore_non_cash_events() -> None:
    first_date = date(2026, 1, 10)
    second_date = date(2026, 2, 10)

    by_day, accumulated = build_dividend_totals(
        [
            _dividend(payment_date=first_date, value=10),
            _dividend(payment_date=None, legacy_payment_date=first_date, value=5),
            _dividend(payment_date=second_date, value=20, dividend_type="JCP"),
            _dividend(payment_date=second_date, value=999, dividend_type="BONIFICACAO"),
            _dividend(
                payment_date=second_date,
                value=999,
                status=DividendStatus.CANCELADO,
            ),
        ]
    )

    assert by_day[first_date] == Decimal("15.00")
    assert by_day[second_date] == Decimal("20.00")
    assert accumulated[first_date] == Decimal("15.00")
    assert accumulated[second_date] == Decimal("35.00")
