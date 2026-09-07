from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.transaction import OperationType
from app.services.benchmark_rate_service import BenchmarkCoverageStatus
from app.services.fixed_income_valuation_service import IncompleteBenchmarkCoverageError
from app.services import portfolio_snapshot_canonical_twr_service as service


class _Scalars:
    def all(self):
        return [
            SimpleNamespace(
                ticker="PETR4",
                asset_type="ACAO",
                operation=OperationType.buy,
                quantity=1,
                price=10,
                fees=0,
                date=date(2026, 9, 7),
                fx_rate=None,
                notes=None,
            )
        ]


class _Result:
    def scalars(self):
        return _Scalars()


class _FixedToday:
    @classmethod
    def today(cls):
        return date(2026, 9, 8)


@pytest.mark.asyncio
async def test_canonical_twr_persists_only_snapshot_columns(monkeypatch):
    persisted_values = []

    async def _capture_upsert(_db, _portfolio_id, _snapshot_date, values):
        persisted_values.append(values)

    monkeypatch.setattr(
        service,
        "load_portfolio_dividend_entitlements",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        service,
        "calculate_canonical_portfolio_totals",
        AsyncMock(
            return_value={
                "market_value": Decimal("10.00"),
                "cost_basis": Decimal("10.00"),
                "invested_total": Decimal("10.00"),
                "realized_pnl": Decimal("0.00"),
                "unrealized_pnl": Decimal("0.00"),
                "total_pnl": Decimal("0.00"),
                "return_pct": Decimal("0.0000"),
                "market_value_by_class": {"ACAO": Decimal("10.00")},
            }
        ),
    )
    monkeypatch.setattr(
        service,
        "has_partial_prices_silent",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(service, "_upsert_enriched_snapshot", _capture_upsert)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.commit = AsyncMock()

    count = await service.backfill_canonical_snapshots_with_returns(
        db,
        portfolio_id=13,
        days_back=0,
    )

    assert count == 1
    assert persisted_values
    assert "market_value_by_class" not in persisted_values[0]
    assert set(persisted_values[0]).issubset(service._SNAPSHOT_COLUMNS)


@pytest.mark.asyncio
async def test_canonical_twr_stops_at_dedicated_coverage_boundary(monkeypatch):
    persisted_dates = []

    async def _capture_upsert(_db, _portfolio_id, snapshot_date, _values):
        persisted_dates.append(snapshot_date)

    totals = {
        "market_value": Decimal("10.00"),
        "cost_basis": Decimal("10.00"),
        "invested_total": Decimal("10.00"),
        "realized_pnl": Decimal("0.00"),
        "unrealized_pnl": Decimal("0.00"),
        "total_pnl": Decimal("0.00"),
        "return_pct": Decimal("0.0000"),
    }
    valuation = AsyncMock(
        side_effect=[
            totals,
            IncompleteBenchmarkCoverageError(
                "CDI",
                date(2026, 9, 7),
                date(2026, 9, 8),
                BenchmarkCoverageStatus.PARTIAL,
            ),
        ]
    )
    monkeypatch.setattr(
        service,
        "load_portfolio_dividend_entitlements",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(service, "calculate_canonical_portfolio_totals", valuation)
    monkeypatch.setattr(
        service,
        "has_partial_prices_silent",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(service, "_upsert_enriched_snapshot", _capture_upsert)
    monkeypatch.setattr(service, "date", _FixedToday)

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    db.commit = AsyncMock()

    count = await service.backfill_canonical_snapshots_with_returns(db, 13)

    assert count == 1
    assert persisted_dates == [date(2026, 9, 7)]
    assert valuation.await_count == 2
    db.commit.assert_awaited_once()
