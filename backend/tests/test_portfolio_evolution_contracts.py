import pytest
from pydantic import ValidationError

from app.schemas.portfolio_evolution import (
    PortfolioClassAvailabilityResponse,
    PortfolioClassDailyEvolutionResponse,
    PortfolioClassMonthlyEvolutionResponse,
    PortfolioClassReconciliationResponse,
    PortfolioDailyEvolutionResponse,
    PortfolioMonthlyEvolutionResponse,
)


@pytest.fixture
def consolidated_daily_payload() -> dict:
    return {
        "date": "2026-07-18",
        "market_value": 1500.0,
        "cost_basis": 1200.0,
        "invested_total": 1300.0,
        "net_external_flow": 100.0,
        "unrealized_pnl": 300.0,
        "realized_pnl": 50.0,
        "total_pnl": 350.0,
        "return_pct": 25.0,
        "dividends_day": 10.0,
        "dividends_accumulated": 80.0,
        "daily_return_pct": 0.5,
        "accumulated_return_pct": 12.5,
        "has_partial_prices": False,
        "return_is_estimated": False,
        "history_source": "portfolio_snapshot",
    }


@pytest.fixture
def class_daily_payload() -> dict:
    return {
        "asset_type": "ACAO",
        "date": "2026-07-18",
        "market_value": 900.0,
        "cost_basis": 700.0,
        "realized_pnl": 30.0,
        "unrealized_pnl": 200.0,
        "net_external_flow": 0.0,
        "dividends_day": 5.0,
        "dividends_accumulated": 45.0,
        "daily_return_pct": 0.4,
        "accumulated_return_pct": 10.2,
        "has_partial_prices": False,
        "return_is_estimated": True,
        "valuation_status": "complete",
        "history_source": "portfolio_class_snapshot",
    }


def test_consolidated_daily_and_monthly_contracts(consolidated_daily_payload: dict) -> None:
    assert PortfolioDailyEvolutionResponse.model_validate(consolidated_daily_payload).date == "2026-07-18"

    monthly = {
        **consolidated_daily_payload,
        "value": 1500.0,
        "invested": 1200.0,
        "period": "2026-07",
        "monthly_return_pct": 1.4,
    }
    assert PortfolioMonthlyEvolutionResponse.model_validate(monthly).period == "2026-07"


def test_class_daily_and_monthly_contracts(class_daily_payload: dict) -> None:
    assert PortfolioClassDailyEvolutionResponse.model_validate(class_daily_payload).asset_type == "ACAO"

    monthly = {
        **class_daily_payload,
        "period": "2026-07",
        "monthly_return_pct": 1.1,
    }
    assert PortfolioClassMonthlyEvolutionResponse.model_validate(monthly).period == "2026-07"


def test_availability_and_reconciliation_contracts() -> None:
    availability = PortfolioClassAvailabilityResponse.model_validate(
        {
            "asset_type": "FII",
            "available": False,
            "engine_supported": True,
            "data_available": False,
            "latest_snapshot_date": None,
            "status": "awaiting_backfill",
            "reason": "Histórico ainda não materializado.",
        }
    )
    assert availability.status == "awaiting_backfill"

    reconciliation = PortfolioClassReconciliationResponse.model_validate(
        {
            "is_reconciled": True,
            "is_comparable": True,
            "status": "evaluated",
            "unsupported_asset_types": [],
            "snapshot_date": "2026-07-18",
            "checks": [
                {
                    "field": "market_value",
                    "expected": 1500.0,
                    "observed": 1500.0,
                    "difference": 0.0,
                    "tolerance": 0.01,
                    "is_reconciled": True,
                }
            ],
        }
    )
    assert reconciliation.checks[0].is_reconciled is True


def test_contracts_reject_unknown_fields_and_sources(consolidated_daily_payload: dict) -> None:
    with pytest.raises(ValidationError):
        PortfolioDailyEvolutionResponse.model_validate(
            {**consolidated_daily_payload, "frontend_calculation": 99.0}
        )

    with pytest.raises(ValidationError):
        PortfolioDailyEvolutionResponse.model_validate(
            {**consolidated_daily_payload, "history_source": "legacy_service"}
        )
