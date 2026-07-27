from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.pre_prod_macro_seed_contract import (
    MacroIndicatorState,
    MacroSeedState,
)
from app.services.pre_prod_macro_seed_service import (
    MacroSeedAlreadyRunningError,
    run_pre_prod_macro_seed,
)

SHA = "a" * 40


def _state(*, duplicates: int = 0, unsupported: tuple[str, ...] = ()) -> MacroSeedState:
    return MacroSeedState(
        total_rows=4,
        indicators=(
            MacroIndicatorState("CDI", 1, "2026-01-01", "2026-01-01", duplicates),
            MacroIndicatorState("SELIC", 1, "2026-01-01", "2026-01-01"),
            MacroIndicatorState("IPCA", 1, "2026-01-01", "2026-01-01"),
            MacroIndicatorState("IGPM", 1, "2026-01-01", "2026-01-01"),
        ),
        unsupported_indicators=unsupported,
    )


@pytest.mark.asyncio
async def test_macro_seed_commits_after_reconciled_inspection() -> None:
    lock_db = AsyncMock()
    lock_db.scalar.return_value = True
    work_db = AsyncMock()
    inspection = AsyncMock(side_effect=[_state(), _state()])
    importer = AsyncMock(return_value={"CDI": 1, "SELIC": 1, "IPCA": 1, "IGPM": 1})

    result = await run_pre_prod_macro_seed(
        run_id="20260726-010203",
        branch="stable-15jun",
        commit_sha=SHA,
        lock_db=lock_db,
        work_db=work_db,
        import_runner=importer,
        inspection_runner=inspection,
    )

    assert result.ok is True
    assert result.errors == ()
    work_db.flush.assert_awaited_once()
    work_db.commit.assert_awaited_once()
    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_macro_seed_rolls_back_when_integrity_is_invalid() -> None:
    lock_db = AsyncMock()
    lock_db.scalar.return_value = True
    work_db = AsyncMock()
    inspection = AsyncMock(
        side_effect=[_state(), _state(duplicates=1, unsupported=("USD",))]
    )
    importer = AsyncMock(return_value={"CDI": 1})

    result = await run_pre_prod_macro_seed(
        run_id="20260726-010204",
        branch="stable-15jun",
        commit_sha=SHA,
        lock_db=lock_db,
        work_db=work_db,
        import_runner=importer,
        inspection_runner=inspection,
    )

    assert result.ok is False
    assert len(result.errors) == 2
    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()
    lock_db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_macro_seed_rejects_concurrent_execution() -> None:
    lock_db = AsyncMock()
    lock_db.scalar.return_value = False
    work_db = AsyncMock()

    with pytest.raises(MacroSeedAlreadyRunningError):
        await run_pre_prod_macro_seed(
            run_id="20260726-010205",
            branch="stable-15jun",
            commit_sha=SHA,
            lock_db=lock_db,
            work_db=work_db,
        )

    work_db.rollback.assert_not_awaited()
    lock_db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_macro_seed_rolls_back_and_unlocks_on_unexpected_error() -> None:
    lock_db = AsyncMock()
    lock_db.scalar.return_value = True
    work_db = AsyncMock()
    inspection = AsyncMock(return_value=_state())
    importer = AsyncMock(side_effect=RuntimeError("provider unavailable"))

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await run_pre_prod_macro_seed(
            run_id="20260726-010206",
            branch="stable-15jun",
            commit_sha=SHA,
            lock_db=lock_db,
            work_db=work_db,
            import_runner=importer,
            inspection_runner=inspection,
        )

    work_db.rollback.assert_awaited_once()
    work_db.commit.assert_not_awaited()
    lock_db.execute.assert_awaited_once()
