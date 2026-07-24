from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services import pre_prod_b3_seed_service as service
from app.services.asset_seed_service import SeedResult
from app.services.b3_historical_market_rebuild_service import (
    B3HistoricalMarketRebuildResult,
)


class _LockSession:
    def __init__(self, acquired: bool = True):
        self.acquired = acquired
        self.execute = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def scalar(self, *_args, **_kwargs):
        return self.acquired


@pytest.mark.asyncio
async def test_stage_excludes_crypto_and_reports_counts(monkeypatch):
    sessions = iter([_LockSession(), _LockSession(), _LockSession()])
    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: next(sessions))
    monkeypatch.setattr(
        service,
        "_counts",
        AsyncMock(
            side_effect=[
                service.B3SeedCounts(assets=0, prices=0),
                service.B3SeedCounts(assets=4, prices=100),
            ]
        ),
    )
    seed = AsyncMock(return_value=SeedResult(created=4))
    history = AsyncMock(
        return_value=B3HistoricalMarketRebuildResult(
            start_year=2020,
            end_year=2026,
            rows_inserted=100,
        )
    )
    monkeypatch.setattr(service, "run_asset_seed", seed)
    monkeypatch.setattr(service, "rebuild_b3_historical_market", history)

    result = await service.run_pre_prod_b3_seed(
        start_year=2020,
        end_year=2026,
        cutoff_date=date(2026, 7, 24),
    )

    assert result.ok is True
    assert result.before.prices == 0
    assert result.after.prices == 100
    assert seed.await_args.kwargs == {"run_backfill": False, "include_crypto": False}
    assert history.await_args.kwargs["cutoff_date"] == date(2026, 7, 24)


@pytest.mark.asyncio
async def test_stage_refuses_concurrent_execution(monkeypatch):
    monkeypatch.setattr(service, "AsyncSessionLocal", lambda: _LockSession(False))

    with pytest.raises(service.B3SeedAlreadyRunningError):
        await service.run_pre_prod_b3_seed(
            start_year=2020,
            end_year=2026,
            cutoff_date=date(2026, 7, 24),
        )


@pytest.mark.asyncio
async def test_stage_requires_cutoff_in_end_year():
    with pytest.raises(ValueError, match="cutoff_date"):
        await service.run_pre_prod_b3_seed(
            start_year=2020,
            end_year=2026,
            cutoff_date=date(2025, 12, 31),
        )
