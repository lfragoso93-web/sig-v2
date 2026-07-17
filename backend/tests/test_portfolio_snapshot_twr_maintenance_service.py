from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.portfolio_snapshot_twr_maintenance_service import (
    _latest_snapshot_has_legacy_zero_twr,
    maintain_twr_snapshots_for_active_portfolios,
)


@pytest.mark.asyncio
async def test_maintenance_processes_only_incomplete_portfolios_and_isolates_errors():
    db = AsyncMock()
    portfolio_result = MagicMock()
    portfolio_result.all.return_value = [
        SimpleRow(1),
        SimpleRow(2),
        SimpleRow(3),
    ]
    db.execute.return_value = portfolio_result

    needs = AsyncMock(side_effect=[True, False, True])
    backfill = AsyncMock(side_effect=[250, RuntimeError("falha controlada")])

    with (
        patch(
            "app.services.portfolio_snapshot_twr_maintenance_service._portfolio_needs_twr_rebuild",
            needs,
        ),
        patch(
            "app.services.portfolio_snapshot_twr_maintenance_service.backfill_snapshots_with_returns",
            backfill,
        ),
    ):
        result = await maintain_twr_snapshots_for_active_portfolios(db)

    assert result == {
        "portfolios": 3,
        "processed": 1,
        "skipped": 1,
        "errors": 1,
        "snapshots": 250,
        "class_snapshots": 0,
    }
    assert backfill.await_count == 2
    db.rollback.assert_awaited_once()


def test_detects_latest_snapshot_overwritten_with_zero_twr():
    previous = SnapshotStub(
        accumulated_return_pct="8.125",
        daily_return_pct="0.45",
        return_pct="7.9",
    )
    latest = SnapshotStub(
        accumulated_return_pct="0",
        daily_return_pct="0",
        return_pct="8.2",
    )

    assert _latest_snapshot_has_legacy_zero_twr(latest, previous) is True


def test_keeps_legitimate_zero_twr_without_prior_performance():
    previous = SnapshotStub(
        accumulated_return_pct="0",
        daily_return_pct="0",
        return_pct="0",
    )
    latest = SnapshotStub(
        accumulated_return_pct="0",
        daily_return_pct="0",
        return_pct="0",
    )

    assert _latest_snapshot_has_legacy_zero_twr(latest, previous) is False


def test_keeps_materialized_nonzero_twr():
    previous = SnapshotStub(
        accumulated_return_pct="4.2",
        daily_return_pct="0.1",
        return_pct="4.0",
    )
    latest = SnapshotStub(
        accumulated_return_pct="4.5",
        daily_return_pct="0.3",
        return_pct="4.4",
    )

    assert _latest_snapshot_has_legacy_zero_twr(latest, previous) is False


class SimpleRow:
    def __init__(self, portfolio_id: int):
        self.id = portfolio_id


class SnapshotStub:
    def __init__(
        self,
        *,
        accumulated_return_pct: str,
        daily_return_pct: str,
        return_pct: str,
    ):
        self.accumulated_return_pct = Decimal(accumulated_return_pct)
        self.daily_return_pct = Decimal(daily_return_pct)
        self.return_pct = Decimal(return_pct)
