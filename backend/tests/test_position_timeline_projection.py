from datetime import date
from decimal import Decimal

from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    project_position_timeline,
)


def _action(
    event_id: str,
    event_date: date,
    kind: CorporateActionKind,
    factor: str,
) -> NormalizedCorporateAction:
    return NormalizedCorporateAction(
        source="test",
        source_event_id=event_id,
        ticker="TEST3",
        event_date=event_date,
        kind=kind,
        quantity_factor=Decimal(factor),
        raw_payload={},
    )


def _buy(day: int, quantity: str, price: str) -> PositionMovement:
    return PositionMovement(
        movement_date=date(2026, 1, day),
        kind=PositionMovementKind.BUY,
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
    )


def _sell(
    day: int,
    quantity: str,
    price: str = "0",
    fees: str = "0",
) -> PositionMovement:
    return PositionMovement(
        movement_date=date(2026, 1, day),
        kind=PositionMovementKind.SELL,
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        fees=Decimal(fees),
    )


def test_split_before_sale_uses_transformed_quantity_and_preserves_cost():
    result = project_position_timeline(
        movements=[_buy(1, "100", "10"), _sell(3, "50", "8")],
        actions=[_action("split", date(2026, 1, 2), CorporateActionKind.SPLIT, "2")],
    )

    assert result.quantity == Decimal(150)
    assert result.total_cost == Decimal(750)
    assert result.average_price == Decimal(5)
    assert result.realized_pnl == Decimal(150)
    assert result.applied_event_ids == ("split",)


def test_sale_fees_reduce_realized_pnl():
    result = project_position_timeline(
        movements=[_buy(1, "10", "10"), _sell(2, "4", "15", fees="1")],
        actions=[],
    )

    assert result.quantity == Decimal(6)
    assert result.total_cost == Decimal(60)
    assert result.realized_pnl == Decimal(19)
    assert len(result.realized_disposals) == 1
    disposal = result.realized_disposals[0]
    assert disposal.quantity_requested == Decimal(4)
    assert disposal.quantity_disposed == Decimal(4)
    assert disposal.gross_proceeds_brl == Decimal(60)
    assert disposal.cost_basis_brl == Decimal(40)
    assert disposal.fees_brl == Decimal(1)
    assert disposal.realized_pnl_brl == Decimal(19)


def test_sale_above_position_records_requested_and_effective_quantities():
    result = project_position_timeline(
        movements=[_buy(1, "10", "10"), _sell(2, "15", "20", fees="1")],
        actions=[],
    )

    disposal = result.realized_disposals[0]
    assert disposal.quantity_requested == Decimal(15)
    assert disposal.quantity_disposed == Decimal(10)
    assert disposal.cost_basis_brl == Decimal(100)
    assert disposal.gross_proceeds_brl == Decimal(200)
    assert disposal.realized_pnl_brl == Decimal(99)
    assert result.realized_pnl == disposal.realized_pnl_brl


def test_disposal_preserves_events_applied_before_sale():
    result = project_position_timeline(
        movements=[_buy(1, "100", "10"), _sell(3, "50", "8")],
        actions=[_action("split", date(2026, 1, 2), CorporateActionKind.SPLIT, "2")],
    )

    assert result.realized_disposals[0].applied_event_ids == ("split",)


def test_event_does_not_apply_to_position_closed_before_event():
    result = project_position_timeline(
        movements=[_buy(1, "100", "10"), _sell(2, "100", "12")],
        actions=[_action("split", date(2026, 1, 3), CorporateActionKind.SPLIT, "2")],
    )

    assert result.quantity == 0
    assert result.total_cost == 0
    assert result.realized_pnl == Decimal(200)
    assert result.applied_event_ids == ()


def test_repurchase_after_event_is_not_transformed_retroactively():
    result = project_position_timeline(
        movements=[
            _buy(1, "100", "10"),
            _sell(2, "100", "12"),
            _buy(4, "30", "20"),
        ],
        actions=[_action("split", date(2026, 1, 3), CorporateActionKind.SPLIT, "2")],
    )

    assert result.quantity == Decimal(30)
    assert result.total_cost == Decimal(600)
    assert result.average_price == Decimal(20)
    assert result.realized_pnl == Decimal(200)
    assert result.applied_event_ids == ()


def test_bonus_and_reverse_split_are_applied_in_chronological_order():
    result = project_position_timeline(
        movements=[_buy(1, "100", "10")],
        actions=[
            _action("bonus", date(2026, 1, 2), CorporateActionKind.STOCK_BONUS, "1.1"),
            _action("reverse", date(2026, 1, 3), CorporateActionKind.REVERSE_SPLIT, "0.5"),
        ],
    )

    assert result.quantity == Decimal("55.0")
    assert result.total_cost == Decimal(1000)
    assert result.realized_pnl == 0
    assert result.applied_event_ids == ("bonus", "reverse")


def test_subscription_is_recorded_without_changing_quantity():
    result = project_position_timeline(
        movements=[_buy(1, "100", "10")],
        actions=[
            _action(
                "subscription",
                date(2026, 1, 2),
                CorporateActionKind.SUBSCRIPTION,
                "1",
            )
        ],
    )

    assert result.quantity == Decimal(100)
    assert result.total_cost == Decimal(1000)
    assert result.realized_pnl == 0
    assert result.subscription_event_ids == ("subscription",)
