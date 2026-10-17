from datetime import date
from decimal import Decimal

import pytest

from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.corporate_event_fractional_resolution import (
    FractionalResolution,
    FractionalResolutionPolicy,
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


def test_full_sale_resets_average_price_before_repurchase():
    result = project_position_timeline(
        movements=[
            _buy(1, "10", "10"),
            _sell(2, "10", "12"),
            _buy(3, "5", "20"),
        ],
        actions=[],
    )

    assert result.quantity == Decimal(5)
    assert result.total_cost == Decimal(100)
    assert result.average_price == Decimal(20)
    assert result.realized_pnl == Decimal(20)


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


def test_cash_settlement_projects_whole_quantity_and_separate_event_cash_flow():
    action = _action(
        "bonus-cash",
        date(2026, 1, 2),
        CorporateActionKind.STOCK_BONUS,
        "1.01",
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
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("0.10"),
            settlement_price=Decimal("4.00"),
            cash_treatment="AUCTION_SETTLEMENT",
        ),
    )

    result = project_position_timeline(
        movements=[_buy(1, "10", "18.53")],
        actions=[action],
    )

    assert result.quantity == Decimal("10")
    expected_fractional_cost = (
        Decimal("185.30") * Decimal("0.10") / Decimal("10.10")
    )
    assert result.total_cost == Decimal("185.30") - expected_fractional_cost
    assert result.realized_pnl == Decimal("0.4000") - expected_fractional_cost

    assert len(result.corporate_action_cash_flows) == 1
    cash_flow = result.corporate_action_cash_flows[0]

    assert cash_flow.source_event_id == "bonus-cash"
    assert cash_flow.event_date == date(2026, 1, 2)
    assert cash_flow.fractional_quantity == Decimal("0.10")
    assert cash_flow.unit_settlement_price_brl == Decimal("4.00")
    assert cash_flow.gross_amount_brl == Decimal("0.4000")
    assert cash_flow.cash_treatment == "AUCTION_SETTLEMENT"
    assert cash_flow.cost_basis_brl == expected_fractional_cost
    assert cash_flow.realized_pnl_brl == (
        Decimal("0.4000") - expected_fractional_cost
    )


def test_pending_settlement_keeps_fraction_out_of_cash_or_realized_projection():
    action = _action(
        "reverse-split-pending",
        date(2026, 1, 2),
        CorporateActionKind.REVERSE_SPLIT,
        "0.2",
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

    result = project_position_timeline(
        movements=[_buy(1, "6", "100")],
        actions=[action],
    )

    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("500")
    assert result.realized_pnl == Decimal("0")
    assert result.corporate_action_cash_flows == ()
    assert len(result.pending_corporate_action_fractions) == 1
    pending = result.pending_corporate_action_fractions[0]
    assert pending.source_event_id == "reverse-split-pending"
    assert pending.fractional_quantity == Decimal("0.2")
    assert pending.cost_basis_brl == Decimal("100")


def test_pending_settlement_derives_fraction_per_portfolio_ledger():
    action = _action(
        "reverse-split-per-portfolio",
        date(2026, 1, 2),
        CorporateActionKind.REVERSE_SPLIT,
        "0.2",
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
        ),
    )

    first = project_position_timeline(movements=[_buy(1, "6", "100")], actions=[action])
    second = project_position_timeline(movements=[_buy(1, "9", "100")], actions=[action])

    assert first.quantity == Decimal("1")
    assert first.pending_corporate_action_fractions[0].fractional_quantity == Decimal("0.2")
    assert second.quantity == Decimal("1")
    assert second.pending_corporate_action_fractions[0].fractional_quantity == Decimal("0.8")
    assert first.realized_pnl == second.realized_pnl == Decimal("0")


def test_pending_settlement_preserves_adjusted_ledger_and_fraction():
    action = _action(
        "reverse-split-adjusted-ledger",
        date(2026, 10, 13),
        CorporateActionKind.REVERSE_SPLIT,
        "0.2",
    )
    action = NormalizedCorporateAction(
        source=action.source,
        source_event_id=action.source_event_id,
        ticker="NIKE34",
        event_date=action.event_date,
        kind=action.kind,
        quantity_factor=action.quantity_factor,
        raw_payload=action.raw_payload,
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.PENDING_SETTLEMENT,
            fractional_quantity=Decimal("1"),
            ledger_basis="ADJUSTED_POST_EVENT",
            fraction_is_post_event_quantity=True,
        ),
    )

    result = project_position_timeline(
        movements=[
            PositionMovement(
                movement_date=date(2026, 10, 1),
                kind=PositionMovementKind.BUY,
                quantity=Decimal("1"),
                unit_price=Decimal("100"),
            )
        ],
        actions=[action],
    )

    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("100")
    assert result.realized_pnl == Decimal("0")
    assert result.pending_corporate_action_fractions[0].fractional_quantity == Decimal("1")
    assert result.pending_corporate_action_fractions[0].cost_basis_brl == Decimal("0")


def test_pending_settlement_keeps_full_cost_for_original_ledger():
    action = _action(
        "reverse-split-cost-pending",
        date(2026, 1, 2),
        CorporateActionKind.REVERSE_SPLIT,
        "0.2",
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
        ),
    )

    result = project_position_timeline(
        movements=[_buy(1, "6", "100")],
        actions=[action],
    )

    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("500")
    assert result.realized_pnl == Decimal("0")
    assert result.pending_corporate_action_fractions[0].fractional_quantity == Decimal("0.2")
    assert result.pending_corporate_action_fractions[0].cost_basis_brl == Decimal("100")


def test_cash_settlement_rejects_fraction_that_differs_from_projected_residue():
    action = _action(
        "bonus-invalid-fraction",
        date(2026, 1, 2),
        CorporateActionKind.STOCK_BONUS,
        "1.01",
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
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("1.10"),
            settlement_price=Decimal("4.00"),
            cash_treatment="AUCTION_SETTLEMENT",
        ),
    )

    with pytest.raises(
        ValueError,
        match="fractional_quantity diverge da fracao projetada",
    ):
        project_position_timeline(
            movements=[_buy(1, "10", "18.53")],
            actions=[action],
        )


def test_cash_settlement_projection_is_deterministic_on_replay():
    action = _action(
        "bonus-replay",
        date(2026, 1, 2),
        CorporateActionKind.STOCK_BONUS,
        "1.01",
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
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("0.10"),
            settlement_price=Decimal("4.00"),
            cash_treatment="AUCTION_SETTLEMENT",
        ),
    )

    first = project_position_timeline(
        movements=[_buy(1, "10", "18.53")],
        actions=[action],
    )
    second = project_position_timeline(
        movements=[_buy(1, "10", "18.53")],
        actions=[action],
    )

    assert second == first
    assert second.quantity == Decimal("10")
    expected_fractional_cost = (
        Decimal("185.30") * Decimal("0.10") / Decimal("10.10")
    )
    assert second.total_cost == Decimal("185.30") - expected_fractional_cost
    assert second.realized_pnl == Decimal("0.4000") - expected_fractional_cost
    assert len(second.corporate_action_cash_flows) == 1
    assert (
        second.corporate_action_cash_flows[0].gross_amount_brl
        == Decimal("0.4000")
    )


def test_nike34_grouping_cash_settlement_is_realized_and_reduces_cost_basis():
    action = _action(
        "nike34-grouping",
        date(2026, 10, 13),
        CorporateActionKind.REVERSE_SPLIT,
        "0.2",
    )
    action = NormalizedCorporateAction(
        source=action.source,
        source_event_id=action.source_event_id,
        ticker="NIKE34",
        event_date=action.event_date,
        kind=action.kind,
        quantity_factor=action.quantity_factor,
        raw_payload=action.raw_payload,
        fractional_resolution=FractionalResolution(
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("0.2"),
            settlement_price=Decimal("80"),
            cash_treatment="AUCTION_SETTLEMENT",
        ),
    )

    result = project_position_timeline(
        movements=[
            _buy(1, "1", "44.50"),
            _buy(2, "2", "32.75"),
            _buy(3, "3", "22.15"),
        ],
        actions=[action],
    )

    expected_fractional_cost = (
        Decimal("176.45") * (Decimal("0.2") / Decimal("1.2"))
    )
    assert result.quantity == Decimal("1")
    assert result.total_cost == Decimal("176.45") - expected_fractional_cost
    assert result.realized_pnl == Decimal("16.0") - expected_fractional_cost
    assert len(result.corporate_action_cash_flows) == 1
    cash_flow = result.corporate_action_cash_flows[0]
    assert cash_flow.fractional_quantity == Decimal("0.2")
    assert cash_flow.gross_amount_brl == Decimal("16.0")
    assert cash_flow.cost_basis_brl == expected_fractional_cost
    assert cash_flow.realized_pnl_brl == (
        Decimal("16.0") - expected_fractional_cost
    )


def test_cash_settlement_requires_complete_evidence():
    action = _action(
        "bonus",
        date(2026, 1, 2),
        CorporateActionKind.STOCK_BONUS,
        "1.01",
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
            policy=FractionalResolutionPolicy.CASH_SETTLEMENT,
            fractional_quantity=Decimal("0.10"),
            settlement_price=None,
            cash_treatment="TEST_ONLY",
        ),
    )

    with pytest.raises(
        ValueError,
        match="CASH_SETTLEMENT exige settlement_price nao negativo",
    ):
        project_position_timeline(
            movements=[_buy(1, "10", "18.53")],
            actions=[action],
        )


def test_no_fractional_residue_rejects_fractional_projected_quantity():
    action = _action(
        "bonus",
        date(2026, 1, 2),
        CorporateActionKind.STOCK_BONUS,
        "1.01",
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
            policy=FractionalResolutionPolicy.NO_FRACTIONAL_RESIDUE,
        ),
    )

    with pytest.raises(
        ValueError,
        match="NO_FRACTIONAL_RESIDUE incompativel com quantidade projetada",
    ):
        project_position_timeline(
            movements=[_buy(1, "10", "18.53")],
            actions=[action],
        )


def test_bonus_without_fractional_resolution_preserves_existing_behavior():
    result = project_position_timeline(
        movements=[_buy(1, "10", "18.53")],
        actions=[
            _action(
                "bonus",
                date(2026, 1, 2),
                CorporateActionKind.STOCK_BONUS,
                "1.01",
            )
        ],
    )

    assert result.quantity == Decimal("10.10")
    assert result.total_cost == Decimal("185.30")
