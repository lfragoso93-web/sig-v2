from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.portfolio_reconciliation_service import reconcile_snapshot_summary


def _snapshot(**overrides):
    data = {
        "snapshot_date": date(2026, 7, 16),
        "market_value": Decimal("12500.00"),
        "cost_basis": Decimal("10000.00"),
        "unrealized_pnl": Decimal("2500.00"),
        "realized_pnl": Decimal("300.00"),
        "dividends_accumulated": Decimal("700.00"),
        "accumulated_return_pct": Decimal("9.8765"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _summary(**overrides):
    data = {
        "total_patrimonio": 12500.00,
        "total_investido": 10000.00,
        "lucro_total": 3500.00,
        "rentabilidade_total": 9.8765,
    }
    data.update(overrides)
    return data


def test_reconciles_canonical_summary_with_snapshot() -> None:
    result = reconcile_snapshot_summary(_snapshot(), _summary())

    assert result["is_reconciled"] is True
    assert result["failed_fields"] == []
    assert result["snapshot_date"] == "2026-07-16"
    assert len(result["checks"]) == 4


def test_reports_divergence_without_mutating_observed_values() -> None:
    summary = _summary(total_patrimonio=12499.50, lucro_total=3498.00)

    result = reconcile_snapshot_summary(_snapshot(), summary)

    assert result["is_reconciled"] is False
    assert result["failed_fields"] == ["total_patrimonio", "lucro_total"]
    patrimonio = next(c for c in result["checks"] if c["field"] == "total_patrimonio")
    assert patrimonio["observed"] == 12499.50
    assert patrimonio["expected"] == 12500.00
    assert patrimonio["difference"] == -0.50


def test_accepts_money_rounding_within_one_cent() -> None:
    result = reconcile_snapshot_summary(
        _snapshot(),
        _summary(total_patrimonio=12499.99),
    )

    assert result["is_reconciled"] is True


def test_rejects_percentage_difference_above_contract_tolerance() -> None:
    result = reconcile_snapshot_summary(
        _snapshot(),
        _summary(rentabilidade_total=9.8767),
    )

    assert result["is_reconciled"] is False
    assert result["failed_fields"] == ["rentabilidade_total"]


def test_optional_positions_and_classes_use_same_snapshot_reference() -> None:
    result = reconcile_snapshot_summary(
        _snapshot(),
        _summary(),
        positions_market_value=12500,
        positions_cost_basis=9999.50,
        classes_market_value=12400,
    )

    assert result["positions_evaluated"] is True
    assert result["classes_evaluated"] is True
    assert result["is_reconciled"] is False
    assert result["failed_fields"] == [
        "positions_cost_basis",
        "classes_market_value",
    ]


def test_optional_consumers_are_explicitly_not_evaluated_when_absent() -> None:
    result = reconcile_snapshot_summary(_snapshot(), _summary())

    assert result["positions_evaluated"] is False
    assert result["classes_evaluated"] is False
