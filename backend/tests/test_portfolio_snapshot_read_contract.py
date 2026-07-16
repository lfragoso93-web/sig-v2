from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.portfolio_snapshot_read_service import snapshot_to_enriched_payload


def _snapshot(**overrides):
    values = {
        "snapshot_date": date(2026, 7, 15),
        "market_value": Decimal("12500.00"),
        "cost_basis": Decimal("10000.00"),
        "invested_total": Decimal("14200.00"),
        "net_external_flow": Decimal("500.00"),
        "unrealized_pnl": Decimal("2500.00"),
        "realized_pnl": Decimal("300.00"),
        "total_pnl": Decimal("3100.00"),
        "return_pct": Decimal("9.5000"),
        "dividends_day": Decimal("25.00"),
        "dividends_accumulated": Decimal("300.00"),
        "daily_return_pct": Decimal("0.250000"),
        "accumulated_return_pct": Decimal("8.750000"),
        "has_partial_prices": False,
        "return_is_estimated": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_monthly_invested_alias_uses_open_position_cost_basis() -> None:
    payload = snapshot_to_enriched_payload(_snapshot(), include_monthly_aliases=True)

    assert payload["value"] == 12500.0
    assert payload["invested"] == 10000.0
    assert payload["invested_total"] == 14200.0
    assert payload["net_external_flow"] == 500.0
    assert payload["history_source"] == "portfolio_snapshot"


def test_snapshot_payload_preserves_quality_and_twr_metadata() -> None:
    payload = snapshot_to_enriched_payload(
        _snapshot(has_partial_prices=True, return_is_estimated=True)
    )

    assert payload["has_partial_prices"] is True
    assert payload["return_is_estimated"] is True
    assert payload["daily_return_pct"] == 0.25
    assert payload["accumulated_return_pct"] == 8.75
