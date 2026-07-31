from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.asset import AssetType
from app.models.transaction import OperationType
from app.services.class_snapshot_position_projection import (
    aggregate_class_positions,
    project_class_positions_at,
)
from app.services.corporate_action_position_reader import CorporateActionPosition


def _transaction(
    *,
    transaction_id: int,
    portfolio_id: int,
    ticker: str,
    asset_type: AssetType,
    operation: OperationType,
    transaction_date: date,
    quantity: str,
    price: str,
    fees: str = "0",
):
    return SimpleNamespace(
        id=transaction_id,
        portfolio_id=portfolio_id,
        ticker=ticker,
        asset_type=asset_type,
        operation=operation,
        date=transaction_date,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal(fees),
        fx_rate=Decimal("1"),
    )


def test_projection_applies_global_split_to_portfolio_transactions_only() -> None:
    transactions = [
        _transaction(
            transaction_id=1,
            portfolio_id=10,
            ticker="ABCD3",
            asset_type=AssetType.ACAO,
            operation=OperationType.buy,
            transaction_date=date(2026, 1, 10),
            quantity="10",
            price="20",
        )
    ]
    actions = {
        "ABCD3": [
            CorporateActionPosition(
                event_id=1,
                ticker="ABCD3",
                event_date=date(2026, 2, 1),
                event_type="SPLIT",
                ratio=Decimal("2"),
            )
        ]
    }

    projected = project_class_positions_at(
        transactions,
        actions,
        target_date=date(2026, 2, 2),
    )

    assert projected["ABCD3"].quantity == Decimal("20")
    assert projected["ABCD3"].cost == Decimal("200")


def test_projection_respects_target_date_and_portfolio_isolation() -> None:
    portfolio_one = [
        _transaction(
            transaction_id=1,
            portfolio_id=1,
            ticker="FUND11",
            asset_type=AssetType.FII,
            operation=OperationType.buy,
            transaction_date=date(2026, 1, 10),
            quantity="5",
            price="100",
        )
    ]
    portfolio_two = [
        _transaction(
            transaction_id=2,
            portfolio_id=2,
            ticker="FUND11",
            asset_type=AssetType.FII,
            operation=OperationType.buy,
            transaction_date=date(2026, 1, 10),
            quantity="9",
            price="100",
        )
    ]
    actions = {
        "FUND11": [
            CorporateActionPosition(
                event_id=1,
                ticker="FUND11",
                event_date=date(2026, 3, 1),
                event_type="BONUS",
                ratio=Decimal("1.10"),
            )
        ]
    }

    before = project_class_positions_at(
        portfolio_one,
        actions,
        target_date=date(2026, 2, 28),
    )
    after_one = project_class_positions_at(
        portfolio_one,
        actions,
        target_date=date(2026, 3, 2),
    )
    after_two = project_class_positions_at(
        portfolio_two,
        actions,
        target_date=date(2026, 3, 2),
    )

    assert before["FUND11"].quantity == Decimal("5")
    assert after_one["FUND11"].quantity == Decimal("5.50")
    assert after_two["FUND11"].quantity == Decimal("9.90")


def test_aggregation_separates_open_positions_and_realized_by_class() -> None:
    transactions = [
        _transaction(
            transaction_id=1,
            portfolio_id=1,
            ticker="ABCD3",
            asset_type=AssetType.ACAO,
            operation=OperationType.buy,
            transaction_date=date(2026, 1, 1),
            quantity="10",
            price="10",
        ),
        _transaction(
            transaction_id=2,
            portfolio_id=1,
            ticker="ABCD3",
            asset_type=AssetType.ACAO,
            operation=OperationType.sell,
            transaction_date=date(2026, 1, 2),
            quantity="4",
            price="15",
            fees="1",
        ),
        _transaction(
            transaction_id=3,
            portfolio_id=1,
            ticker="FUND11",
            asset_type=AssetType.FII,
            operation=OperationType.buy,
            transaction_date=date(2026, 1, 1),
            quantity="2",
            price="100",
        ),
    ]

    projected = project_class_positions_at(
        transactions,
        {},
        target_date=date(2026, 1, 3),
    )
    open_by_class, realized_by_class = aggregate_class_positions(projected.values())

    assert [item.ticker for item in open_by_class[AssetType.ACAO]] == ["ABCD3"]
    assert [item.ticker for item in open_by_class[AssetType.FII]] == ["FUND11"]
    assert realized_by_class[AssetType.ACAO] == Decimal("19")
