from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.pre_prod_fx_seed_contract import FxPairState, FxSeedState
from app.services.pre_prod_fx_seed_preparation import FxSeedPreparationResult
from app.services.pre_prod_fx_seed_service import (
    FxSeedAlreadyRunningError,
    run_pre_prod_fx_seed,
)

RUN_ID = "20260727-120000"
BRANCH = "stable-15jun"
COMMIT_SHA = "a" * 40


def _state(*, duplicate_rows: int = 0, unsupported_pairs: tuple[str, ...] = ()) -> FxSeedState:
    return FxSeedState(
        total_rows=1,
        pairs=(
            FxPairState(
                pair="USD-BRL",
                rows=1,
                first_date="2026-07-24",
                last_date="2026-07-24",
                duplicate_rows=duplicate_rows,
            ),
        ),
        unsupported_pairs=unsupported_pairs,
    )


def _prepared() -> FxSeedPreparationResult:
    return FxSeedPreparationResult(
        pair="USD-BRL",
        requested_start_date="2026-07-24",
        requested_end_date="2026-07-25",
        fetched_rows=1,
        persisted_rows=1,
        first_date="2026-07-24",
        last_date="2026-07-24",
    )


@pytest.mark.asyncio
async def test_run_fx_seed_commits_and_releases_lock_on_success() -> None:
    lock_db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(),
    )
    work_db = SimpleNamespace(
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    inspection_runner = AsyncMock(side_effect=[_state(), _state()])
    preparation_runner = AsyncMock(return_value=_prepared())

    result = await run_pre_prod_fx_seed(
        run_id=RUN_ID,
        branch=BRANCH,
        commit_sha=COMMIT_SHA,
        start_date="2026-07-24",
        end_date="2026-07-25",
        lock_db=lock_db,
        work_db=work_db,
        preparation_runner=preparation_runner,
        inspection_runner=inspection_runner,
    )

    assert result.ok is True
    assert result.imported == {"USD-BRL": 1}
    work_db.flush.assert_awaited_once()
    work_db.commit.assert_awaited_once()
    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_fx_seed_rolls_back_when_final_state_is_invalid() -> None:
    lock_db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(),
    )
    work_db = SimpleNamespace(
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    inspection_runner = AsyncMock(
        side_effect=[_state(), _state(duplicate_rows=1)]
    )

    result = await run_pre_prod_fx_seed(
        run_id=RUN_ID,
        branch=BRANCH,
        commit_sha=COMMIT_SHA,
        start_date="2026-07-24",
        end_date="2026-07-25",
        lock_db=lock_db,
        work_db=work_db,
        preparation_runner=AsyncMock(return_value=_prepared()),
        inspection_runner=inspection_runner,
    )

    assert result.ok is False
    assert result.errors == ("fx_rates contém 1 linha(s) duplicada(s)",)
    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_fx_seed_rejects_concurrent_execution() -> None:
    lock_db = SimpleNamespace(
        scalar=AsyncMock(return_value=False),
        execute=AsyncMock(),
    )
    work_db = SimpleNamespace(
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    with pytest.raises(FxSeedAlreadyRunningError, match="já está em execução"):
        await run_pre_prod_fx_seed(
            run_id=RUN_ID,
            branch=BRANCH,
            commit_sha=COMMIT_SHA,
            start_date="2026-07-24",
            end_date="2026-07-25",
            lock_db=lock_db,
            work_db=work_db,
        )

    work_db.flush.assert_not_awaited()
    work_db.commit.assert_not_awaited()
    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_fx_seed_rolls_back_and_releases_lock_on_exception() -> None:
    lock_db = SimpleNamespace(
        scalar=AsyncMock(return_value=True),
        execute=AsyncMock(),
    )
    work_db = SimpleNamespace(
        flush=AsyncMock(),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )

    with pytest.raises(RuntimeError, match="falha controlada"):
        await run_pre_prod_fx_seed(
            run_id=RUN_ID,
            branch=BRANCH,
            commit_sha=COMMIT_SHA,
            start_date="2026-07-24",
            end_date="2026-07-25",
            lock_db=lock_db,
            work_db=work_db,
            preparation_runner=AsyncMock(
                side_effect=RuntimeError("falha controlada")
            ),
            inspection_runner=AsyncMock(return_value=_state()),
        )

    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()
    lock_db.execute.assert_awaited_once()
