from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.pre_prod_treasury_seed_contract import (
    TreasurySeedCounts,
    TreasurySeedCoverage,
)
from app.services.pre_prod_treasury_seed_service import (
    TreasurySeedAlreadyRunningError,
    run_pre_prod_treasury_seed,
)


class _LockSession:
    def __init__(self, acquired: bool = True) -> None:
        self.acquired = acquired
        self.execute = AsyncMock()

    async def scalar(self, *_args, **_kwargs):
        return self.acquired


@pytest.mark.asyncio
async def test_orchestrator_runs_catalog_before_history_and_reports_state() -> None:
    order: list[str] = []
    before = TreasurySeedCounts(assets=2, aliases=1, prices=10)
    after = TreasurySeedCounts(assets=2, aliases=1, prices=12)
    coverage = TreasurySeedCoverage(
        first_price_date="2020-01-02",
        last_price_date="2026-07-24",
        priced_assets=2,
    )
    inspection = AsyncMock(
        side_effect=[
            (before, TreasurySeedCoverage()),
            (after, coverage),
        ]
    )

    async def catalog_runner(_db):
        order.append("catalog")
        return {"created": 0, "updated": 0, "errors": 0}

    async def history_runner():
        order.append("history")
        return {"imported": 2, "empty_payloads": 0, "unresolved_assets": []}

    lock_db = _LockSession()
    result = await run_pre_prod_treasury_seed(
        lock_db=lock_db,
        inspection_db=object(),
        catalog_db=object(),
        catalog_runner=catalog_runner,
        history_runner=history_runner,
        inspection_runner=inspection,
    )

    assert order == ["catalog", "history"]
    assert result.ok is True
    assert result.before.prices == 10
    assert result.after.prices == 12
    assert result.coverage.last_price_date == "2026-07-24"
    assert inspection.await_count == 2
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_refuses_concurrent_execution() -> None:
    lock_db = _LockSession(acquired=False)

    with pytest.raises(TreasurySeedAlreadyRunningError):
        await run_pre_prod_treasury_seed(
            lock_db=lock_db,
            inspection_db=object(),
            catalog_db=object(),
            catalog_runner=AsyncMock(),
            history_runner=AsyncMock(),
            inspection_runner=AsyncMock(),
        )

    lock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_releases_lock_when_runner_fails() -> None:
    counts = TreasurySeedCounts(assets=2, aliases=1, prices=10)
    inspection = AsyncMock(return_value=(counts, TreasurySeedCoverage()))
    lock_db = _LockSession()

    async def failing_catalog(_db):
        raise RuntimeError("catalog failed")

    with pytest.raises(RuntimeError, match="catalog failed"):
        await run_pre_prod_treasury_seed(
            lock_db=lock_db,
            inspection_db=object(),
            catalog_db=object(),
            catalog_runner=failing_catalog,
            history_runner=AsyncMock(),
            inspection_runner=inspection,
        )

    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_marks_unresolved_integrity_as_failure() -> None:
    before = TreasurySeedCounts(assets=2, aliases=1, prices=10)
    after = TreasurySeedCounts(
        assets=2,
        aliases=1,
        prices=10,
        duplicate_prices=1,
    )
    inspection = AsyncMock(
        side_effect=[
            (before, TreasurySeedCoverage()),
            (after, TreasurySeedCoverage(priced_assets=2)),
        ]
    )

    result = await run_pre_prod_treasury_seed(
        lock_db=_LockSession(),
        inspection_db=object(),
        catalog_db=object(),
        catalog_runner=AsyncMock(return_value={"errors": 1}),
        history_runner=AsyncMock(
            return_value={
                "empty_payloads": 1,
                "unresolved_assets": ["tesouro-selic-2031"],
            }
        ),
        inspection_runner=inspection,
    )

    assert result.ok is False
    assert len(result.errors) == 4
