from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.models.asset import AssetType
from app.models.dividend import DividendStatus
from app.services.portfolio_class_reconciliation_service import _check
from app.services.portfolio_class_snapshot_read_service import class_snapshot_payload
from app.services.portfolio_class_snapshot_service import (
    ClassPositionState,
    _group_received_dividends,
    class_twr_availability,
)


def test_position_state_preserves_cost_and_realized_result() -> None:
    state = ClassPositionState(AssetType.ACAO)
    state.buy(Decimal("10"), Decimal("10"), Decimal("2"))
    state.sell(Decimal("4"), Decimal("15"), Decimal("1"))

    assert state.quantity == Decimal("6")
    assert state.cost == Decimal("61.20")
    assert state.realized_pnl == Decimal("18.20")


def test_availability_refuses_dedicated_history_estimates() -> None:
    rows = class_twr_availability(
        [AssetType.ACAO, AssetType.FII, AssetType.TESOURO_DIRETO, AssetType.RENDA_FIXA]
    )
    by_type = {row["asset_type"]: row for row in rows}

    assert by_type[AssetType.ACAO.value]["available"] is True
    assert by_type[AssetType.FII.value]["status"] == "available"
    assert by_type[AssetType.TESOURO_DIRETO.value]["available"] is False
    assert by_type[AssetType.RENDA_FIXA.value]["status"] == "dedicated_history_not_available"


def test_received_dividends_are_grouped_by_class_and_payment_date() -> None:
    dividends = [
        SimpleNamespace(
            ticker="ABCD3",
            status=DividendStatus.RECEBIDO,
            dividend_type="DIVIDENDO",
            payment_date=date(2026, 7, 10),
            date_pagamento=None,
            net_value=Decimal("12.34"),
            total_received=None,
            total_value=Decimal("13.00"),
        ),
        SimpleNamespace(
            ticker="FUND11",
            status=DividendStatus.RECEBIDO,
            dividend_type="RENDIMENTO",
            payment_date=date(2026, 7, 10),
            date_pagamento=None,
            net_value=Decimal("5.00"),
            total_received=None,
            total_value=Decimal("5.00"),
        ),
        SimpleNamespace(
            ticker="ABCD3",
            status="A_RECEBER",
            dividend_type="DIVIDENDO",
            payment_date=date(2026, 7, 10),
            date_pagamento=None,
            net_value=Decimal("99.00"),
            total_received=None,
            total_value=Decimal("99.00"),
        ),
    ]

    grouped = _group_received_dividends(
        dividends,
        {"ABCD3": AssetType.ACAO, "FUND11": AssetType.FII},
    )

    assert grouped[(AssetType.ACAO, date(2026, 7, 10))] == Decimal("12.34")
    assert grouped[(AssetType.FII, date(2026, 7, 10))] == Decimal("5.00")


def test_class_snapshot_payload_exposes_quality_and_twr() -> None:
    snapshot = SimpleNamespace(
        asset_type="ACAO",
        snapshot_date=date(2026, 7, 15),
        market_value=Decimal("1200.00"),
        cost_basis=Decimal("1000.00"),
        realized_pnl=Decimal("50.00"),
        unrealized_pnl=Decimal("200.00"),
        net_external_flow=Decimal("0.00"),
        dividends_day=Decimal("10.00"),
        dividends_accumulated=Decimal("80.00"),
        daily_return_pct=Decimal("1.234567"),
        accumulated_return_pct=Decimal("8.765432"),
        has_partial_prices=False,
        return_is_estimated=True,
        valuation_status="complete",
    )

    payload = class_snapshot_payload(snapshot)

    assert payload["history_source"] == "portfolio_class_snapshot"
    assert payload["daily_return_pct"] == 1.234567
    assert payload["accumulated_return_pct"] == 8.765432
    assert payload["return_is_estimated"] is True
    assert payload["valuation_status"] == "complete"


def test_reconciliation_check_preserves_sign_and_tolerance() -> None:
    reconciled = _check("market_value", Decimal("100.00"), Decimal("100.01"))
    failed = _check("market_value", Decimal("100.00"), Decimal("99.98"))

    assert reconciled["is_reconciled"] is True
    assert reconciled["difference"] == 0.01
    assert failed["is_reconciled"] is False
    assert failed["difference"] == -0.02
