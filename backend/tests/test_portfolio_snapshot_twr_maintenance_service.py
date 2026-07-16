from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.portfolio_snapshot_twr_maintenance_service import (
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
    }
    assert backfill.await_count == 2
    db.rollback.assert_awaited_once()


class SimpleRow:
    def __init__(self, portfolio_id: int):
        self.id = portfolio_id
