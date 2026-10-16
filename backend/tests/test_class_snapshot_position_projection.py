from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.asset import AssetType
from app.models.transaction import OperationType
from app.services.class_snapshot_position_projection import (
    aggregate_class_positions,
    project_class_positions_at,
)
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_event_fractional_resolution import (
    FractionalResolution,
    FractionalResolutionPolicy,
)


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
        fx_rate=Decimal(1),
    )


def _action(
    *,
    source_event_id: str,
    ticker: str,
    event_date: date,
    kind: CorporateActionKind,
    quantity_factor: str,
) -> NormalizedCorporateAction:
    return NormalizedCorporateAction(
        source="test",
        source_event_id=source_event_id,
        ticker=ticker,
        event_date=event_date,
        kind=kind,
        quantity_factor=Decimal(quantity_factor),
        raw_payload={},
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
            _action(
                source_event_id="split-1",
                ticker="ABCD3",
                event_date=date(2026, 2, 1),
                kind=CorporateActionKind.SPLIT,
                quantity_factor="2",
            )
        ]
    }

    projected = project_class_positions_at(
        transactions,
        actions,
        target_date=date(2026, 2, 2),
    )

    assert projected["ABCD3"].quantity == Decimal(20)
    assert projected["ABCD3"].cost == Decimal(200)


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
            _action(
                source_event_id="bonus-1",
                ticker="FUND11",
                event_date=date(2026, 3, 1),
                kind=CorporateActionKind.STOCK_BONUS,
                quantity_factor="1.10",
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

    assert before["FUND11"].quantity == Decimal(5)
    assert after_one["FUND11"].quantity == Decimal("5.50")
    assert after_two["FUND11"].quantity == Decimal("9.90")


def test_snapshot_projection_excludes_unsettled_fraction_from_value_and_cost() -> None:
    transactions = [
        _transaction(
            transaction_id=1,
            portfolio_id=1,
            ticker="NIKE34",
            asset_type=AssetType.BDR,
            operation=OperationType.buy,
            transaction_date=date(2026, 10, 1),
            quantity="6",
            price="100",
        )
    ]
    action = _action(
        source_event_id="reverse-split-pending",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor="0.2",
    )
    action = NormalizedCorporateAction(
        source=action.source,
        source_event_id=action.source_event_id,
        ticker=action.ticker,
        event_date=action.event_date,
        kind=action.kind,
        quantity_factor=action.quantity_factor,
        raw_payload=action.raw_payload,
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.PENDING_SETTLEMENT,
            fractional_quantity=Decimal("0.2"),
        ),
    )

    projected = project_class_positions_at(
        transactions,
        {"NIKE34": [action]},
        target_date=date(2026, 10, 14),
    )

    assert projected["NIKE34"].quantity == Decimal("1.0")
    assert projected["NIKE34"].cost == Decimal("500.0")
    assert projected["NIKE34"].has_pending_fraction is True


def test_snapshot_projection_retains_pending_fraction_without_open_shares() -> None:
    transactions = [
        _transaction(
            transaction_id=1,
            portfolio_id=1,
            ticker="NIKE34",
            asset_type=AssetType.BDR,
            operation=OperationType.buy,
            transaction_date=date(2026, 10, 1),
            quantity="1",
            price="100",
        )
    ]
    action = _action(
        source_event_id="reverse-split-pending-all",
        ticker="NIKE34",
        event_date=date(2026, 10, 13),
        kind=CorporateActionKind.REVERSE_SPLIT,
        quantity_factor="0.2",
    )
    action = NormalizedCorporateAction(
        source=action.source,
        source_event_id=action.source_event_id,
        ticker=action.ticker,
        event_date=action.event_date,
        kind=action.kind,
        quantity_factor=action.quantity_factor,
        raw_payload=action.raw_payload,
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.PENDING_SETTLEMENT,
            fractional_quantity=Decimal("0.2"),
        ),
    )

    projected = project_class_positions_at(
        transactions,
        {"NIKE34": [action]},
        target_date=date(2026, 10, 14),
    )

    assert projected["NIKE34"].quantity == Decimal("0")
    assert projected["NIKE34"].cost == Decimal("0")
    assert projected["NIKE34"].has_pending_fraction is True


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
    assert realized_by_class[AssetType.ACAO] == Decimal(19)
