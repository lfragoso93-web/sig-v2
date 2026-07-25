from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cli import pre_prod_treasury_seed as cli
from app.services.pre_prod_treasury_seed_contract import TREASURY_SEED_BRANCH
from app.services.pre_prod_treasury_seed_service import TreasurySeedAlreadyRunningError

RUN_ID = "20260725-170000"
COMMIT_SHA = "a" * 40


@asynccontextmanager
async def _session():
    yield object()


@pytest.fixture(autouse=True)
def _sessions(monkeypatch):
    monkeypatch.setattr(cli, "AsyncSessionLocal", _session)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                run_id=RUN_ID,
                branch=TREASURY_SEED_BRANCH,
                commit_sha=COMMIT_SHA,
            )
        ),
    )


@pytest.mark.asyncio
async def test_cli_returns_zero_and_prints_contract_on_success(monkeypatch, capsys):
    result = SimpleNamespace(
        ok=True,
        to_dict=lambda: {
            "schema_version": "pre-prod-treasury-seed.v1",
            "run_id": RUN_ID,
            "branch": TREASURY_SEED_BRANCH,
            "commit_sha": COMMIT_SHA,
            "ok": True,
        },
    )
    runner = AsyncMock(return_value=result)
    monkeypatch.setattr(cli, "run_pre_prod_treasury_seed", runner)

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "pre-prod-treasury-seed.v1"
    assert payload["run_id"] == RUN_ID
    assert payload["branch"] == TREASURY_SEED_BRANCH
    assert payload["commit_sha"] == COMMIT_SHA
    assert payload["ok"] is True
    runner.assert_awaited_once_with(
        run_id=RUN_ID,
        branch=TREASURY_SEED_BRANCH,
        commit_sha=COMMIT_SHA,
        lock_db=runner.await_args.kwargs["lock_db"],
        work_db=runner.await_args.kwargs["work_db"],
    )


@pytest.mark.asyncio
async def test_cli_rejects_invalid_identity_before_opening_sessions(monkeypatch, capsys):
    sessions = AsyncMock()
    monkeypatch.setattr(cli, "AsyncSessionLocal", sessions)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                run_id="invalid",
                branch=TREASURY_SEED_BRANCH,
                commit_sha=COMMIT_SHA,
            )
        ),
    )

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_OPERATIONAL_FAILURE
    assert "run_id" in json.loads(capsys.readouterr().out)["error"]
    sessions.assert_not_called()


@pytest.mark.asyncio
async def test_cli_returns_operational_failure_for_invalid_result(monkeypatch, capsys):
    result = SimpleNamespace(ok=False, to_dict=lambda: {"ok": False, "errors": ["integridade"]})
    monkeypatch.setattr(cli, "run_pre_prod_treasury_seed", AsyncMock(return_value=result))

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_OPERATIONAL_FAILURE
    assert json.loads(capsys.readouterr().out)["ok"] is False


@pytest.mark.asyncio
async def test_cli_returns_distinct_code_for_concurrent_execution(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_pre_prod_treasury_seed",
        AsyncMock(side_effect=TreasurySeedAlreadyRunningError("estágio Tesouro já está em execução")),
    )

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_ALREADY_RUNNING
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"ok": False, "error": "estágio Tesouro já está em execução"}


@pytest.mark.asyncio
async def test_cli_returns_operational_code_for_runtime_error(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_pre_prod_treasury_seed",
        AsyncMock(side_effect=RuntimeError("fonte oficial indisponível")),
    )

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_OPERATIONAL_FAILURE
    assert json.loads(capsys.readouterr().out)["error"] == "fonte oficial indisponível"


@pytest.mark.asyncio
async def test_cli_redacts_unexpected_exception_message(monkeypatch, capsys):
    monkeypatch.setattr(
        cli,
        "run_pre_prod_treasury_seed",
        AsyncMock(side_effect=OSError("postgresql://usuario:senha@host/banco")),
    )

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_UNEXPECTED_FAILURE
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["error"] == "falha inesperada no estágio Tesouro"
    assert payload["type"] == "OSError"
    assert "senha" not in output
