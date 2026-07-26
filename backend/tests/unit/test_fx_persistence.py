from unittest.mock import AsyncMock

import pytest

from app.services.fx_service import PAIR_USD_BRL, persist_usd_brl_rate


@pytest.mark.asyncio
async def test_persist_usd_brl_rate_commits_by_default() -> None:
    db = AsyncMock()

    await persist_usd_brl_rate(db, "2026-07-25", 5.432198765)

    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()

    _, params = db.execute.await_args.args
    assert params["pair"] == PAIR_USD_BRL
    assert params["rate"] == 5.43219877


@pytest.mark.asyncio
async def test_persist_usd_brl_rate_does_not_commit_when_disabled() -> None:
    db = AsyncMock()

    await persist_usd_brl_rate(
        db,
        "2026-07-25",
        5.43,
        commit=False,
    )

    db.execute.assert_awaited_once()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_persist_usd_brl_rate_rolls_back_and_raises_with_internal_commit() -> None:
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await persist_usd_brl_rate(db, "2026-07-25", 5.43)

    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_usd_brl_rate_leaves_rollback_to_external_transaction() -> None:
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        await persist_usd_brl_rate(
            db,
            "2026-07-25",
            5.43,
            commit=False,
        )

    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()
