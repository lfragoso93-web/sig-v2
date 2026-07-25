from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest
from app.services import pre_prod_treasury_seed_service as service
from app.services.pre_prod_treasury_seed_contract import (
    TREASURY_SEED_BRANCH,
    TreasurySeedCounts,
    TreasurySeedCoverage,
)

RUN_ID = "20260725-170000"
COMMIT_SHA = "a" * 40


class _LockSession:
    def __init__(self, acquired: bool = True) -> None:
        self.acquired = acquired
        self.execute = AsyncMock()

    async def scalar(self, *_args, **_kwargs):
        return self.acquired


class _WorkSession:
    def __init__(self) -> None:
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


def _identity() -> dict[str, str]:
    return {
        "run_id": RUN_ID,
        "branch": TREASURY_SEED_BRANCH,
        "commit_sha": COMMIT_SHA,
    }


def _state(*, prices: int = 10, duplicate_prices: int = 0):
    counts = TreasurySeedCounts(
        assets=2,
        aliases=1,
        prices=prices,
        duplicate_prices=duplicate_prices,
    )
    coverage = TreasurySeedCoverage(
        first_price_date="2020-01-02" if prices else None,
        last_price_date="2026-07-24" if prices else None,
        priced_assets=2 if prices else 0,
    )
    return counts, coverage


@pytest.mark.asyncio
async def test_orchestrator_runs_real_order_and_commits_once() -> None:
    order: list[str] = []
    before, before_coverage = _state(prices=10)
    after, coverage = _state(prices=12)
    inspection = AsyncMock(
        side_effect=[
            (before, before_coverage),
            (after, coverage),
        ]
    )

    async def catalog_runner(_db):
        order.append("catalog")
        return {"created": 0, "updated": 0, "errors": 0}

    async def history_runner(_db):
        order.append("history")
        return {
            "imported": 2,
            "empty_payloads": 3,
            "required_empty_payloads": 0,
            "expected_empty_payloads": 3,
            "unresolved_assets": [],
        }

    lock_db = _LockSession()
    work_db = _WorkSession()
    result = await service.run_pre_prod_treasury_seed(
        **_identity(),
        lock_db=lock_db,
        work_db=work_db,
        catalog_runner=catalog_runner,
        history_runner=history_runner,
        inspection_runner=inspection,
    )

    assert order == ["catalog", "history"]
    assert result.ok is True
    assert result.run_id == RUN_ID
    assert result.branch == TREASURY_SEED_BRANCH
    assert result.commit_sha == COMMIT_SHA
    assert result.before.prices == 10
    assert result.after.prices == 12
    inspection.assert_has_awaits([call(work_db), call(work_db)])
    work_db.flush.assert_awaited_once()
    work_db.commit.assert_awaited_once()
    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_refuses_concurrent_execution_without_touching_work_db() -> None:
    lock_db = _LockSession(acquired=False)
    work_db = _WorkSession()

    with pytest.raises(service.TreasurySeedAlreadyRunningError):
        await service.run_pre_prod_treasury_seed(
            **_identity(),
            lock_db=lock_db,
            work_db=work_db,
            catalog_runner=AsyncMock(),
            history_runner=AsyncMock(),
            inspection_runner=AsyncMock(),
        )

    work_db.flush.assert_not_awaited()
    work_db.commit.assert_not_awaited()
    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrator_rolls_back_and_releases_lock_when_runner_raises() -> None:
    before, coverage = _state(prices=10)
    inspection = AsyncMock(return_value=(before, coverage))
    lock_db = _LockSession()
    work_db = _WorkSession()

    async def failing_catalog(_db):
        raise RuntimeError("catalog failed")

    with pytest.raises(RuntimeError, match="catalog failed"):
        await service.run_pre_prod_treasury_seed(
            **_identity(),
            lock_db=lock_db,
            work_db=work_db,
            catalog_runner=failing_catalog,
            history_runner=AsyncMock(),
            inspection_runner=inspection,
        )

    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_orchestrator_rolls_back_invalid_final_state() -> None:
    before, before_coverage = _state(prices=10)
    after, coverage = _state(prices=10, duplicate_prices=1)
    inspection = AsyncMock(
        side_effect=[
            (before, before_coverage),
            (after, coverage),
        ]
    )
    work_db = _WorkSession()

    result = await service.run_pre_prod_treasury_seed(
        **_identity(),
        lock_db=_LockSession(),
        work_db=work_db,
        catalog_runner=AsyncMock(return_value={"errors": 1}),
        history_runner=AsyncMock(
            return_value={
                "empty_payloads": 2,
                "required_empty_payloads": 1,
                "expected_empty_payloads": 1,
                "unresolved_assets": ["tesouro-selic-2031"],
            }
        ),
        inspection_runner=inspection,
    )

    assert result.ok is False
    assert result.run_id == RUN_ID
    assert result.branch == TREASURY_SEED_BRANCH
    assert result.commit_sha == COMMIT_SHA
    assert len(result.errors) == 4
    assert "1 payloads vazios bloqueantes" in result.errors[2]
    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()


def test_collect_errors_keeps_legacy_empty_payload_contract_blocking() -> None:
    after, _coverage = _state(prices=10)

    errors = service._collect_errors(
        catalog={"errors": 0},
        history={"empty_payloads": 1, "unresolved_assets": []},
        after=after,
    )

    assert errors == ["histórico retornou 1 payloads vazios bloqueantes"]


@pytest.mark.asyncio
async def test_real_runners_share_session_and_disable_internal_commits(monkeypatch) -> None:
    db = object()
    catalog_result = SimpleNamespace(to_dict=lambda: {"errors": 0, "created": 1})
    catalog = AsyncMock(return_value=catalog_result)
    history = AsyncMock(return_value={"imported": 3})
    monkeypatch.setattr(service, "sync_treasury_catalog_v2", catalog)
    monkeypatch.setattr(service, "rebuild_official_treasury_history", history)

    catalog_payload = await service._run_real_catalog(db)
    history_payload = await service._run_real_history(db)

    assert catalog_payload == {"errors": 0, "created": 1}
    assert history_payload == {"imported": 3}
    catalog.assert_awaited_once_with(db, commit=False)
    history.assert_awaited_once_with(db, commit=False)
