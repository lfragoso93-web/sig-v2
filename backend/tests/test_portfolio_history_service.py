from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.portfolio_history_service import monthly_snapshot_payload


def test_monthly_snapshot_payload_uses_closed_snapshot_values() -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 7, 31),
        market_value=Decimal("20739.67"),
        cost_basis=Decimal("22149.25"),
        unrealized_pnl=Decimal("-1409.58"),
        realized_pnl=Decimal("250.00"),
        total_pnl=Decimal("-1159.58"),
        return_pct=Decimal("-5.2345"),
        daily_return_pct=Decimal("0.125000"),
        accumulated_return_pct=Decimal("8.765400"),
        has_partial_prices=False,
        return_is_estimated=True,
    )

    payload = monthly_snapshot_payload(snapshot)

    assert payload["date"] == "2026-07-31"
    assert payload["period"] == "2026-07"
    assert payload["value"] == 20739.67
    assert payload["invested"] == 22149.25
    assert payload["capital_result"] == -1409.58
    assert payload["accumulated_return_pct"] == 8.7654
    assert payload["history_source"] == "portfolio_snapshot"


def test_capital_result_is_derived_instead_of_trusting_duplicate_field() -> None:
    snapshot = SimpleNamespace(
        snapshot_date=date(2026, 6, 30),
        market_value=Decimal("1100.00"),
        cost_basis=Decimal("1000.00"),
        unrealized_pnl=Decimal("9999.00"),
        realized_pnl=Decimal("0.00"),
        total_pnl=Decimal("100.00"),
        return_pct=Decimal("10.0000"),
        daily_return_pct=Decimal("0.000000"),
        accumulated_return_pct=Decimal("10.000000"),
        has_partial_prices=False,
        return_is_estimated=False,
    )

    assert monthly_snapshot_payload(snapshot)["capital_result"] == 100.0
