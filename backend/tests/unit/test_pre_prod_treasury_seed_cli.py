from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cli import pre_prod_treasury_seed as cli
from app.services.pre_prod_treasury_seed_service import TreasurySeedAlreadyRunningError


@asynccontextmanager
async def _session():
    yield object()


@pytest.fixture(autouse=True)
def _sessions(monkeypatch):
    monkeypatch.setattr(cli, "AsyncSessionLocal", _session)
    monkeypatch.setattr(cli, "_parser", lambda: SimpleNamespace(parse_args=lambda: None))


@pytest.mark.asyncio
async def test_cli_returns_zero_and_prints_contract_on_success(monkeypatch, capsys):
    result = SimpleNamespace(ok=True, to_dict=lambda: {"schema_version": "pre-prod-treasury-seed.v1", "ok": True})
    runner = AsyncMock(return_value=result)
    monkeypatch.setattr(cli, "run_pre_prod_treasury_seed", runner)

    exit_code = await cli._main()

    assert exit_code == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "pre-prod-treasury-seed.v1"
    assert payload["ok"] is True
    runner.assert_awaited_once()


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
    payload = json.loads(capsys.readouterr().out)
    assert payload["error"] == "falha inesperada no estágio Tesouro"
    assert payload["type"] == "OSError"
    assert "senha" not in capsys.readouterr().out
