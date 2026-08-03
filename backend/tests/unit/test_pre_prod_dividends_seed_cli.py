from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.cli import pre_prod_dividends_seed as cli
from app.services.pre_prod_dividends_seed_persistence import (
    DividendsSeedAlreadyRunningError,
)
from app.services.pre_prod_dividends_seed_service import (
    DividendsSeedUnexpectedStageError,
)

RUN_ID = "20260728-180000"
BRANCH = "stable-15jun"
COMMIT_SHA = "a" * 40


@asynccontextmanager
async def _session():
    yield object()


class _Client:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


@pytest.fixture(autouse=True)
def _dependencies(monkeypatch):
    monkeypatch.setattr(cli, "AsyncSessionLocal", _session)
    monkeypatch.setattr(cli.httpx, "AsyncClient", lambda **kwargs: _Client())
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                run_id=RUN_ID,
                branch=BRANCH,
                commit_sha=COMMIT_SHA,
                start_date="2026-01-01",
                end_date="2026-12-31",
            )
        ),
    )


@pytest.mark.asyncio
async def test_cli_prints_contract_on_success(monkeypatch, capsys):
    result = SimpleNamespace(
        ok=True,
        to_dict=lambda: {
            "schema_version": "pre-prod-dividends-seed.v2",
            "run_id": RUN_ID,
            "ok": True,
        },
    )
    runner = AsyncMock(return_value=result)
    monkeypatch.setattr(cli, "run_pre_prod_dividends_seed", runner)

    assert await cli._main() == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "pre-prod-dividends-seed.v2"
    assert payload["ok"] is True
    assert runner.await_args.kwargs["start_date"].isoformat() == "2026-01-01"
    assert runner.await_args.kwargs["end_date"].isoformat() == "2026-12-31"
    assert len(runner.await_args.kwargs["providers"]) == 2


@pytest.mark.asyncio
async def test_cli_validates_identity_before_opening_resources(monkeypatch, capsys):
    session_factory = AsyncMock()
    monkeypatch.setattr(cli, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                run_id=RUN_ID,
                branch="main",
                commit_sha=COMMIT_SHA,
                start_date="2026-01-01",
                end_date="2026-12-31",
            )
        ),
    )
    runner = AsyncMock()
    monkeypatch.setattr(cli, "run_pre_prod_dividends_seed", runner)

    assert await cli._main() == cli.EXIT_OPERATIONAL_FAILURE
    assert "stable-15jun" in json.loads(capsys.readouterr().out)["error"]
    session_factory.assert_not_called()
    runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_cli_rejects_invalid_window_before_opening_resources(monkeypatch, capsys):
    session_factory = AsyncMock()
    monkeypatch.setattr(cli, "AsyncSessionLocal", session_factory)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                run_id=RUN_ID,
                branch=BRANCH,
                commit_sha=COMMIT_SHA,
                start_date="2026-12-31",
                end_date="2026-01-01",
            )
        ),
    )

    assert await cli._main() == cli.EXIT_OPERATIONAL_FAILURE
    assert "posterior" in json.loads(capsys.readouterr().out)["error"]
    session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_cli_has_distinct_exit_for_lock_contention(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_pre_prod_dividends_seed",
        AsyncMock(side_effect=DividendsSeedAlreadyRunningError("em execução")),
    )

    assert await cli._main() == cli.EXIT_ALREADY_RUNNING
    assert json.loads(capsys.readouterr().out)["error"] == "em execução"


@pytest.mark.asyncio
async def test_cli_redacts_unexpected_error(monkeypatch, capsys):
    database_error = RuntimeError("postgresql://user:secret@host/db")
    database_error.sqlstate = "42883"
    staged_error = DividendsSeedUnexpectedStageError("initial_inspection")
    staged_error.__cause__ = database_error
    monkeypatch.setattr(
        cli,
        "run_pre_prod_dividends_seed",
        AsyncMock(side_effect=staged_error),
    )

    assert await cli._main() == cli.EXIT_UNEXPECTED_FAILURE
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["error"] == "falha inesperada no estágio de proventos"
    assert payload["stage"] == "initial_inspection"
    assert payload["type"] == "RuntimeError"
    assert payload["sqlstate"] == "42883"
    assert "secret" not in output
