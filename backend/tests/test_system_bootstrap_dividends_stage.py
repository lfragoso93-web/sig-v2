from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.system_bootstrap_dividends_stage import (
    DIVIDENDS_BOOTSTRAP_AUTH_ENV,
    DIVIDENDS_HISTORY_START_DATE,
    SystemBootstrapDividendsGateError,
    run_system_bootstrap_dividends_stage,
)
from app.services.system_bootstrap_execution_context import (
    SystemBootstrapExecutionContext,
)


_CONTEXT = SystemBootstrapExecutionContext(
    run_id="20260808-000000",
    branch="stable-15jun",
    commit_sha="a" * 40,
)


@pytest.mark.asyncio
async def test_dividends_stage_is_blocked_without_explicit_authorization(
    monkeypatch,
) -> None:
    monkeypatch.delenv(DIVIDENDS_BOOTSTRAP_AUTH_ENV, raising=False)
    seed_runner = AsyncMock()

    with pytest.raises(SystemBootstrapDividendsGateError, match="#226"):
        await run_system_bootstrap_dividends_stage(
            _CONTEXT,
            end_date=DIVIDENDS_HISTORY_START_DATE,
            seed_runner=seed_runner,
        )

    seed_runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_dividends_stage_reuses_strict_seed_when_authorized() -> None:
    result = SimpleNamespace(
        ok=True,
        schema_version="pre-prod-dividends-seed.v2",
        coverage=SimpleNamespace(
            first_ex_date="2001-01-02",
            last_ex_date="2026-08-08",
            assets_with_events=123,
        ),
        global_persistence={"created": 10, "updated": 2, "unchanged": 30},
    )
    seed_runner = AsyncMock(return_value=result)

    detail = await run_system_bootstrap_dividends_stage(
        _CONTEXT,
        end_date=DIVIDENDS_HISTORY_START_DATE,
        authorized=True,
        seed_runner=seed_runner,
    )

    assert "schema=pre-prod-dividends-seed.v2" in detail
    assert "assets_with_events=123" in detail
    seed_runner.assert_awaited_once()
    call = seed_runner.await_args.kwargs
    assert call["run_id"] == _CONTEXT.run_id
    assert call["branch"] == _CONTEXT.branch
    assert call["commit_sha"] == _CONTEXT.commit_sha
    assert call["start_date"] == DIVIDENDS_HISTORY_START_DATE
    assert call["end_date"] == DIVIDENDS_HISTORY_START_DATE
    assert len(call["providers"]) == 2
