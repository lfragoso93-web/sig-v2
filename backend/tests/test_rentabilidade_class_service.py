from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services import rentabilidade_class_service as service


@pytest.mark.asyncio
async def test_class_contract_separates_intraday_result_from_closed_twr(monkeypatch) -> None:
    async def fake_positions(db, portfolio_id, user_id):
        return [
            {
                "asset_type": "ACAO",
                "total_value": 1200.0,
                "total_invested": 1000.0,
                "capital_result_value": 200.0,
                "capital_result_pct": 20.0,
                "received_dividends": 50.0,
                "total_result_value": 250.0,
                "total_result_pct": 25.0,
                "positions": [{"ticker": "ABCD3"}],
            }
        ]

    async def fake_snapshots(db, portfolio_id):
        return {
            "ACAO": SimpleNamespace(
                daily_return_pct=Decimal("1.250000"),
                accumulated_return_pct=Decimal("8.750000"),
                snapshot_date=date(2026, 7, 15),
                has_partial_prices=False,
                return_is_estimated=True,
            )
        }

    async def fake_availability(db, portfolio_id):
        return [
            {
                "asset_type": "ACAO",
                "available": True,
                "status": "available",
                "reason": None,
            }
        ]

    monkeypatch.setattr(service, "get_canonical_portfolio_positions", fake_positions)
    monkeypatch.setattr(service, "_latest_snapshots_by_class", fake_snapshots)
    monkeypatch.setattr(service, "get_class_twr_availability", fake_availability)

    rows = await service.get_canonical_class_performance(object(), 1, 10)

    assert rows == [
        {
            "asset_type": "ACAO",
            "current_value": 1200.0,
            "cost_basis": 1000.0,
            "capital_result_value": 200.0,
            "capital_result_pct": 20.0,
            "received_dividends": 50.0,
            "total_result_value": 250.0,
            "total_result_pct": 25.0,
            "allocation_pct": 100.0,
            "asset_count": 1,
            "twr_available": True,
            "daily_twr_pct": 1.25,
            "accumulated_twr_pct": 8.75,
            "performance_as_of": "2026-07-15",
            "has_partial_prices": False,
            "return_is_estimated": True,
            "performance_status": "available",
            "performance_reason": None,
            "performance_source": "portfolio_class_snapshot",
        }
    ]


@pytest.mark.asyncio
async def test_class_contract_does_not_promote_simple_result_when_twr_missing(monkeypatch) -> None:
    async def fake_positions(db, portfolio_id, user_id):
        return [
            {
                "asset_type": "RENDA_FIXA",
                "total_value": 1100.0,
                "total_invested": 1000.0,
                "capital_result_value": 100.0,
                "capital_result_pct": 10.0,
                "positions": [],
            }
        ]

    async def fake_snapshots(db, portfolio_id):
        return {}

    async def fake_availability(db, portfolio_id):
        return [
            {
                "asset_type": "RENDA_FIXA",
                "available": False,
                "status": "dedicated_history_not_available",
                "reason": "Valuation histórico dedicado indisponível.",
            }
        ]

    monkeypatch.setattr(service, "get_canonical_portfolio_positions", fake_positions)
    monkeypatch.setattr(service, "_latest_snapshots_by_class", fake_snapshots)
    monkeypatch.setattr(service, "get_class_twr_availability", fake_availability)

    row = (await service.get_canonical_class_performance(object(), 1, 10))[0]

    assert row["capital_result_pct"] == 10.0
    assert row["twr_available"] is False
    assert row["accumulated_twr_pct"] is None
    assert row["performance_source"] is None
    assert row["performance_status"] == "dedicated_history_not_available"
