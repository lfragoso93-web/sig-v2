from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.transaction import OperationType
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.snapshot_position_projection import project_snapshot_positions


def _tx(
    *,
    portfolio_id: int,
    day: int,
    operation: OperationType,
    quantity: str,
    price: str,
):
    return SimpleNamespace(
        portfolio_id=portfolio_id,
        ticker="TEST3",
        asset_type="ACAO",
        operation=operation,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal("0"),
        date=date(2026, 1, day),
        currency="BRL",
        fx_rate=None,
    )


def _split(day: int, factor: str) -> NormalizedCorporateAction:
    return NormalizedCorporateAction(
        source="test",
        source_event_id=f"split-{day}",
        ticker="TEST3",
        event_date=date(2026, 1, day),
        kind=CorporateActionKind.SPLIT,
        quantity_factor=Decimal(factor),
        raw_payload={},
    )


def test_snapshot_projection_uses_only_transactions_supplied_for_portfolio():
    portfolio_one = [
        _tx(
            portfolio_id=1,
            day=1,
            operation=OperationType.buy,
            quantity="100",
            price="10",
        )
    ]
    portfolio_two = [
        _tx(
            portfolio_id=2,
            day=1,
            operation=OperationType.buy,
            quantity="30",
            price="20",
        )
    ]
    actions = {"TEST3": (_split(2, "2"),)}

    first = project_snapshot_positions(
        transactions=portfolio_one,
        actions_by_ticker=actions,
        target_date=date(2026, 1, 3),
    )
    second = project_snapshot_positions(
        transactions=portfolio_two,
        actions_by_ticker=actions,
        target_date=date(2026, 1, 3),
    )

    assert first["TEST3"][0].quantity == Decimal("200")
    assert first["TEST3"][0].total_cost == Decimal("1000")
    assert second["TEST3"][0].quantity == Decimal("60")
    assert second["TEST3"][0].total_cost == Decimal("600")


def test_snapshot_projection_respects_target_date():
    result = project_snapshot_positions(
        transactions=[
            _tx(
                portfolio_id=1,
                day=1,
                operation=OperationType.buy,
                quantity="100",
                price="10",
            )
        ],
        actions_by_ticker={"TEST3": (_split(3, "2"),)},
        target_date=date(2026, 1, 2),
    )

    projection = result["TEST3"][0]
    assert projection.quantity == Decimal("100")
    assert projection.total_cost == Decimal("1000")
    assert projection.applied_event_ids == ()


def test_snapshot_projection_preserves_realized_pnl_after_split():
    result = project_snapshot_positions(
        transactions=[
            _tx(
                portfolio_id=1,
                day=1,
                operation=OperationType.buy,
                quantity="100",
                price="10",
            ),
            _tx(
                portfolio_id=1,
                day=3,
                operation=OperationType.sell,
                quantity="50",
                price="8",
            ),
        ],
        actions_by_ticker={"TEST3": (_split(2, "2"),)},
        target_date=date(2026, 1, 4),
    )

    projection = result["TEST3"][0]
    assert projection.quantity == Decimal("150")
    assert projection.total_cost == Decimal("750")
    assert projection.realized_pnl == Decimal("150")
