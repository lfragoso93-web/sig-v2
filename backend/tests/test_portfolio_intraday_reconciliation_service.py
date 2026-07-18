from unittest.mock import AsyncMock, patch

import pytest

from app.services.portfolio_intraday_reconciliation_service import (
    get_intraday_reconciliation,
    reconcile_intraday_consumers,
)


def _summary(**overrides) -> dict:
    data = {
        "total_patrimonio": 12500.0,
        "total_investido": 10000.0,
        "ganho_nao_realizado": 2500.0,
        "rentabilidade_total": 9.8765,
        "valuation_updated_at": "2026-07-18T12:00:00+00:00",
    }
    data.update(overrides)
    return data


def _groups() -> list[dict]:
    return [
        {
            "label": "Ações",
            "total_value": 7500.0,
            "total_invested": 6000.0,
            "capital_result_value": 1500.0,
            "positions": [{"asset_type": "ACAO"}],
        },
        {
            "label": "FIIs",
            "total_value": 5000.0,
            "total_invested": 4000.0,
            "capital_result_value": 1000.0,
            "positions": [{"asset_type": "FII"}],
        },
    ]


def _distribution() -> list[dict]:
    return [
        {"asset_type": "ACAO", "value": 7500.0},
        {"asset_type": "FII", "value": 5000.0},
    ]


def test_reconciles_summary_positions_and_distribution_intraday():
    result = reconcile_intraday_consumers(
        _summary(),
        _groups(),
        _distribution(),
    )

    assert result["is_reconciled"] is True
    assert result["failed_fields"] == []
    assert result["valuation_mode"] == "intraday"
    assert result["snapshot_evaluated"] is False
    assert result["money_tolerance"] == 0.01
    assert len(result["checks"]) == 6


def test_accepts_aggregate_rounding_within_one_cent():
    groups = _groups()
    groups[1]["total_value"] = 4999.99
    groups[1]["capital_result_value"] = 999.99

    result = reconcile_intraday_consumers(
        _summary(ganho_nao_realizado=2499.99),
        groups,
        _distribution(),
    )

    assert result["is_reconciled"] is True


def test_reports_consumer_and_internal_group_divergences():
    groups = _groups()
    groups[1]["total_invested"] = 3999.50

    result = reconcile_intraday_consumers(
        _summary(),
        groups,
        _distribution(),
    )

    assert result["is_reconciled"] is False
    assert result["failed_fields"] == [
        "positions.total_investido",
        "groups.FII.capital_result_value",
    ]


def test_does_not_compare_snapshot_or_twr_fields():
    result = reconcile_intraday_consumers(
        _summary(rentabilidade_total=-999.0, snapshot_date="1999-01-01"),
        _groups(),
        _distribution(),
    )

    assert result["is_reconciled"] is True
    assert all("rentabilidade" not in check["field"] for check in result["checks"])


@pytest.mark.asyncio
async def test_get_intraday_reconciliation_materializes_all_contracts():
    with (
        patch(
            "app.services.portfolio_intraday_reconciliation_service.get_canonical_portfolio_summary",
            new=AsyncMock(return_value=_summary()),
        ) as summary_mock,
        patch(
            "app.services.portfolio_intraday_reconciliation_service.get_canonical_portfolio_positions",
            new=AsyncMock(return_value=_groups()),
        ) as positions_mock,
        patch(
            "app.services.portfolio_intraday_reconciliation_service.get_asset_distribution",
            new=AsyncMock(return_value=_distribution()),
        ) as distribution_mock,
    ):
        result = await get_intraday_reconciliation(AsyncMock(), 46, 7)

    summary_mock.assert_awaited_once()
    positions_mock.assert_awaited_once()
    distribution_mock.assert_awaited_once()
    assert result["portfolio_id"] == 46
    assert result["valuation_updated_at"] == "2026-07-18T12:00:00+00:00"
    assert result["is_reconciled"] is True
