from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.transaction import OperationType
from app.services.snapshot_position_projection import (
    project_snapshot_positions,
    project_transaction_timelines,
)


def _tx(
    *,
    ticker: str,
    operation: OperationType,
    tx_date: date,
    quantity: str,
    price: str,
    fees: str = "0",
    asset_type: str = "ACAO",
    currency: str = "BRL",
):
    return SimpleNamespace(
        ticker=ticker,
        operation=operation,
        date=tx_date,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal(fees),
        asset_type=asset_type,
        currency=currency,
        fx_rate=None,
    )


def test_irpf_cutoff_projection_preserves_partial_sale_cost_basis() -> None:
    transactions = [
        _tx(
            ticker="PETR4",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="200",
            price="30",
            fees="20",
        ),
        _tx(
            ticker="PETR4",
            operation=OperationType.sell,
            tx_date=date(2024, 6, 10),
            quantity="50",
            price="35",
        ),
    ]

    projected = project_snapshot_positions(
        transactions=transactions,
        actions_by_ticker={},
        target_date=date(2024, 12, 31),
    )
    position, asset_type, is_usd = projected["PETR4"]

    assert position.quantity == Decimal("150")
    assert position.total_cost == Decimal("4515")
    assert position.average_price == Decimal("30.1")
    assert asset_type == "ACAO"
    assert is_usd is False


def test_irpf_cutoff_projection_excludes_transactions_after_year_end() -> None:
    transactions = [
        _tx(
            ticker="VALE3",
            operation=OperationType.buy,
            tx_date=date(2024, 12, 20),
            quantity="10",
            price="50",
        ),
        _tx(
            ticker="VALE3",
            operation=OperationType.buy,
            tx_date=date(2025, 1, 3),
            quantity="5",
            price="60",
        ),
    ]

    projected = project_snapshot_positions(
        transactions=transactions,
        actions_by_ticker={},
        target_date=date(2024, 12, 31),
    )
    position, _, _ = projected["VALE3"]

    assert position.quantity == Decimal("10")
    assert position.total_cost == Decimal("500")


def test_irpf_cutoff_projection_resets_cost_after_full_exit_and_repurchase() -> None:
    transactions = [
        _tx(
            ticker="ABCD3",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="100",
            price="10",
        ),
        _tx(
            ticker="ABCD3",
            operation=OperationType.sell,
            tx_date=date(2024, 3, 10),
            quantity="100",
            price="12",
        ),
        _tx(
            ticker="ABCD3",
            operation=OperationType.buy,
            tx_date=date(2024, 8, 10),
            quantity="40",
            price="20",
            fees="4",
        ),
    ]

    projected = project_snapshot_positions(
        transactions=transactions,
        actions_by_ticker={},
        target_date=date(2024, 12, 31),
    )
    position, _, _ = projected["ABCD3"]

    assert position.quantity == Decimal("40")
    assert position.total_cost == Decimal("804")
    assert position.average_price == Decimal("20.1")


def test_irpf_realized_projection_keeps_closed_tickers() -> None:
    transactions = [
        _tx(
            ticker="VALE3",
            operation=OperationType.buy,
            tx_date=date(2024, 1, 10),
            quantity="100",
            price="50",
        ),
        _tx(
            ticker="VALE3",
            operation=OperationType.sell,
            tx_date=date(2024, 6, 10),
            quantity="100",
            price="60",
            fees="10",
        ),
    ]

    projected = project_transaction_timelines(
        transactions=transactions,
        actions_by_ticker={},
        target_date=date(2024, 12, 31),
    )
    position, _, _ = projected["VALE3"]

    assert position.quantity == Decimal("0")
    assert position.total_cost == Decimal("0")
    assert position.realized_pnl == Decimal("990")
