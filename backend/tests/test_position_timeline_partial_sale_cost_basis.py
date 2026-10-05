from datetime import date
from decimal import Decimal

from app.services.position_timeline_projection import (
    PositionMovement,
    PositionMovementKind,
    project_position_timeline,
)


def test_partial_sale_uses_moving_average_cost_including_buy_fees_and_sell_fee():
    projection = project_position_timeline(
        movements=[
            PositionMovement(
                movement_date=date(2026, 1, 2),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("100"),
                unit_price=Decimal("20.00"),
                fees=Decimal("5.00"),
                ticker="PETR4",
                asset_type="ACAO",
            ),
            PositionMovement(
                movement_date=date(2026, 1, 10),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("50"),
                unit_price=Decimal("22.00"),
                fees=Decimal("3.00"),
                ticker="PETR4",
                asset_type="ACAO",
            ),
            PositionMovement(
                movement_date=date(2026, 2, 1),
                kind=PositionMovementKind.SELL,
                quantity=Decimal("60"),
                unit_price=Decimal("25.00"),
                fees=Decimal("4.00"),
                ticker="PETR4",
                asset_type="ACAO",
            ),
        ],
        actions=[],
        through_date=date(2026, 2, 28),
    )

    assert projection.quantity == Decimal("90")
    assert projection.total_cost == Decimal("1864.80")
    assert projection.average_price == Decimal("20.72")
    assert projection.realized_pnl == Decimal("252.80")

    disposal = projection.realized_disposals[0]
    assert disposal.quantity_disposed == Decimal("60")
    assert disposal.cost_basis_brl == Decimal("1243.20")
    assert disposal.gross_proceeds_brl == Decimal("1500.00")
    assert disposal.fees_brl == Decimal("4.00")
    assert disposal.realized_pnl_brl == Decimal("252.80")
