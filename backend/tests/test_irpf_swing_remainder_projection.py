"""Testes da projeção read-only de excedentes Swing."""

from datetime import date
from decimal import Decimal

from app.services.irpf_day_trade_matcher import DayTradeMatch
from app.services.irpf_swing_remainder_projection import (
    project_swing_remainder_disposals,
)
from app.services.position_timeline_projection import CanonicalRealizedDisposal


def _disposal(
    *,
    transaction_id: int | None = 2,
    quantity: str = "10",
) -> CanonicalRealizedDisposal:
    qty = Decimal(quantity)
    return CanonicalRealizedDisposal(
        transaction_id=transaction_id,
        ticker="BOVA11",
        asset_type="ETF",
        disposal_date=date(2024, 5, 2),
        quantity_requested=qty,
        quantity_disposed=qty,
        unit_proceeds_brl=Decimal(15),
        gross_proceeds_brl=qty * Decimal(15),
        cost_basis_brl=qty * Decimal(10),
        fees_brl=Decimal(2),
        realized_pnl_brl=qty * Decimal(5) - Decimal(2),
        currency="BRL",
        gross_proceeds_original_currency=qty * Decimal(15),
        applied_event_ids=("split-1",),
    )


def _match(quantity: str) -> DayTradeMatch:
    return DayTradeMatch(
        ticker="BOVA11",
        trade_date=date(2024, 5, 2),
        buy_transaction_id=1,
        sell_transaction_id=2,
        quantity=Decimal(quantity),
        buy_unit_price_brl=Decimal(10),
        sell_unit_price_brl=Decimal(15),
        allocated_buy_fees_brl=Decimal(0),
        allocated_sell_fees_brl=Decimal(0),
    )


def test_fully_matched_disposal_is_removed_from_swing_view() -> None:
    assert project_swing_remainder_disposals([_disposal()], [_match("10")]) == ()


def test_partial_match_scales_financial_values_proportionally() -> None:
    [remainder] = project_swing_remainder_disposals(
        [_disposal()],
        [_match("4")],
    )

    assert remainder.quantity_requested == Decimal(6)
    assert remainder.quantity_disposed == Decimal(6)
    assert remainder.gross_proceeds_brl == Decimal(90)
    assert remainder.cost_basis_brl == Decimal(60)
    assert remainder.fees_brl == Decimal("1.2")
    assert remainder.realized_pnl_brl == Decimal("28.8")
    assert remainder.gross_proceeds_original_currency == Decimal(90)
    assert remainder.applied_event_ids == ("split-1",)


def test_unmatched_and_unidentified_disposals_are_preserved() -> None:
    unmatched = _disposal(transaction_id=7)
    unidentified = _disposal(transaction_id=None)

    result = project_swing_remainder_disposals(
        [unmatched, unidentified],
        [_match("4")],
    )

    assert result == (unidentified, unmatched)
