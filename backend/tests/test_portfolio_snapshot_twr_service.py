from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import cast

from app.models.asset import AssetType
from app.models.transaction import OperationType, Transaction
from app.services.portfolio_snapshot_twr_service import (
    build_open_quote_requirements,
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
    asset_type: AssetType = AssetType.ACAO,
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
            asset_type=asset_type,
            fx_rate=None,
            notes=notes,
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


def test_open_quote_requirements_ignore_closed_and_no_quote_positions() -> None:
    target = date(2026, 1, 10)
    requirements = build_open_quote_requirements(
        [
            _tx(
                operation=OperationType.buy,
                quantity=10,
                price=10,
                tx_date=date(2026, 1, 2),
                ticker="PETR4",
                asset_type=AssetType.ACAO,
            ),
            _tx(
                operation=OperationType.buy,
                quantity=1,
                price=1000,
                tx_date=date(2026, 1, 2),
                ticker="TESOURO-SELIC-2031",
                asset_type=AssetType.TESOURO_DIRETO,
            ),
            _tx(
                operation=OperationType.buy,
                quantity=5,
                price=20,
                tx_date=date(2026, 1, 2),
                ticker="CLOSED11",
                asset_type=AssetType.FII,
            ),
            _tx(
                operation=OperationType.sell,
                quantity=5,
                price=21,
                tx_date=date(2026, 1, 9),
                ticker="CLOSED11",
                asset_type=AssetType.FII,
            ),
        ],
        target,
    )

    assert requirements == [("PETR4", AssetType.ACAO)]


def test_future_transactions_do_not_enter_quote_requirements() -> None:
    target = date(2026, 1, 10)
    requirements = build_open_quote_requirements(
        [
            _tx(
                operation=OperationType.buy,
                quantity=1,
                price=10,
                tx_date=date(2026, 1, 11),
                ticker="VALE3",
            )
        ],
        target,
    )

    assert requirements == []
