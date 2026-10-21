from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.transaction import OperationType
from app.services.corporate_action_engine import (
    CorporateActionKind,
    NormalizedCorporateAction,
)
from app.services.snapshot_position_projection import project_transaction_timelines


def _bonus_action() -> NormalizedCorporateAction:
    return NormalizedCorporateAction(
        source="b3",
        source_event_id="klabin-bonus-2025",
        ticker="KLBN11",
        event_date=date(2025, 12, 22),
        kind=CorporateActionKind.STOCK_BONUS,
        quantity_factor=Decimal("1.01"),
        raw_payload={},
        component_bonus={
            "record_date": "2025-12-17",
            "credit_date": "2025-12-22",
            "settlement_date": "2026-02-24",
            "bonus_factor": "0.01",
            "bonus_cost_per_share_brl": "12.94564988922",
            "unit_ticker": "KLBN11",
            "unit_asset_type": "ACAO",
            "unit_isin_code": "US0231351067",
            "unit_composition": {"ON": "1", "PN": "4"},
            "components": [
                {
                    "component": "ON",
                    "ticker": "KLBN3",
                    "asset_type": "ACAO",
                    "isin_code": "US0378331005",
                    "units_per_position": "1",
                    "settlement_price_brl": "3.942352337",
                },
                {
                    "component": "PN",
                    "ticker": "KLBN4",
                    "asset_type": "ACAO",
                    "isin_code": "US5949181045",
                    "units_per_position": "4",
                    "settlement_price_brl": "3.942611212",
                },
            ],
        },
    )


def _transaction(
    *, ticker: str, operation: OperationType, quantity: str, price: str, day: date, asset_type: str = "ACAO", txid: int = 1
) -> SimpleNamespace:
    return SimpleNamespace(
        id=txid,
        ticker=ticker,
        asset_type=asset_type,
        currency="BRL",
        fx_rate=None,
        operation=operation,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal("0"),
        date=day,
    )


def test_component_bonus_creates_units_and_residual_share_legs_with_cost():
    projected = project_transaction_timelines(
        transactions=(
            _transaction(
                ticker="KLBN11",
                operation=OperationType.buy,
                quantity="150",
                price="100",
                day=date(2025, 12, 1),
            ),
        ),
        actions_by_ticker={"KLBN11": (_bonus_action(),)},
        target_date=date(2025, 12, 31),
    )

    unit_position = projected["KLBN11"][0]
    pn_position = projected["KLBN4"][0]
    assert unit_position.quantity == Decimal("151")
    assert pn_position.quantity == Decimal("2")
    assert pn_position.total_cost == Decimal("25.891299778440")
    assert "klabin-bonus-2025" in unit_position.applied_event_ids
    assert "klabin-bonus-2025" in pn_position.applied_event_ids
    rights = unit_position.component_bonus_cash_rights
    assert len(rights) == 1
    assert rights[0].component == "ON"
    assert rights[0].quantity == Decimal("0.50")
    assert rights[0].gross_amount_brl == Decimal("1.97117616850")
    assert rights[0].attributed_cost_brl == Decimal("6.472824944610")
    assert rights[0].status == "CALCULATED_NOT_CONFIRMED"


def test_fractional_component_rights_do_not_become_cash_or_ledger_movements():
    projected = project_transaction_timelines(
        transactions=(
            _transaction(
                ticker="KLBN11",
                operation=OperationType.buy,
                quantity="10",
                price="100",
                day=date(2025, 12, 1),
            ),
        ),
        actions_by_ticker={"KLBN11": (_bonus_action(),)},
        target_date=date(2025, 12, 31),
    )

    units, _, _ = projected["KLBN11"]
    assert units.quantity == Decimal("10")
    assert units.total_cost == Decimal("1000")
    assert "KLBN3" not in projected
    assert "KLBN4" not in projected
    assert sum(
        (right.gross_amount_brl for right in units.component_bonus_cash_rights),
        Decimal(0),
    ) == Decimal("1.97127971850")
    assert all(
        right.status == "CALCULATED_NOT_CONFIRMED"
        for right in units.component_bonus_cash_rights
    )


def test_bonus_asset_legs_start_on_issuer_credit_date():
    before_credit = project_transaction_timelines(
        transactions=(
            _transaction(
                ticker="KLBN11",
                operation=OperationType.buy,
                quantity="150",
                price="100",
                day=date(2025, 12, 1),
            ),
        ),
        actions_by_ticker={"KLBN11": (_bonus_action(),)},
        target_date=date(2025, 12, 21),
    )

    assert before_credit["KLBN11"][0].quantity == Decimal("150")
    assert "KLBN4" not in before_credit


def test_later_sale_of_component_bonus_shares_uses_issuer_cost_basis():
    projected = project_transaction_timelines(
        transactions=(
            _transaction(
                ticker="KLBN11",
                operation=OperationType.buy,
                quantity="150",
                price="100",
                day=date(2025, 12, 1),
            ),
            _transaction(
                ticker="KLBN4",
                operation=OperationType.sell,
                quantity="1",
                price="20",
                day=date(2026, 3, 1),
                txid=2,
            ),
        ),
        actions_by_ticker={"KLBN11": (_bonus_action(),)},
        target_date=date(2026, 3, 2),
    )

    pn_position = projected["KLBN4"][0]
    assert pn_position.quantity == Decimal("1")
    assert pn_position.realized_pnl == Decimal("7.05435011078")
    assert pn_position.realized_disposals[0].cost_basis_brl == Decimal(
        "12.94564988922"
    )
