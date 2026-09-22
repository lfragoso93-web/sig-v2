from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cli import pre_prod_corporate_events_seed as cli


class _Result:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _Session:
    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.execute = AsyncMock(
            side_effect=[_Result(["AMOB3"]), _Result([SimpleNamespace(
                ticker="AMOB3",
                asset_type="ACAO",
            )])]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _configure(monkeypatch, session, *, execute: bool):
    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: session)
    monkeypatch.setattr(
        cli,
        "_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(portfolio_id=7, execute=execute)
        ),
    )


def test_seed_cli_defaults_to_dry_run() -> None:
    arguments = cli._parser().parse_args(["--portfolio-id", "7"])

    assert arguments.execute is False


def test_seed_cli_requires_explicit_execute_for_persistence() -> None:
    arguments = cli._parser().parse_args(["--portfolio-id", "7", "--execute"])

    assert arguments.execute is True


@pytest.mark.asyncio
async def test_seed_cli_dry_run_rolls_back_and_reports_zero_writes(
    monkeypatch, capsys
) -> None:
    session = _Session()
    _configure(monkeypatch, session, execute=False)
    monkeypatch.setattr(
        cli,
        "sync_corporate_events_for_asset",
        AsyncMock(return_value=[object()]),
    )

    await cli._main()

    output = capsys.readouterr().out
    assert '"dry_run": true' in output
    assert '"database_writes_executed": 0' in output
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_cli_execute_commits_and_counts_writes(monkeypatch, capsys) -> None:
    session = _Session()
    _configure(monkeypatch, session, execute=True)
    monkeypatch.setattr(
        cli,
        "sync_corporate_events_for_asset",
        AsyncMock(return_value=[object()]),
    )

    await cli._main()

    output = capsys.readouterr().out
    assert '"dry_run": false' in output
    assert '"database_writes_executed": 1' in output
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_cli_rolls_back_failed_asset_and_reports_error(
    monkeypatch, capsys
) -> None:
    session = _Session()
    _configure(monkeypatch, session, execute=True)
    monkeypatch.setattr(
        cli,
        "sync_corporate_events_for_asset",
        AsyncMock(side_effect=RuntimeError("provider indisponivel")),
    )

    await cli._main()

    payload = capsys.readouterr().out
    assert '"database_writes_executed": 0' in payload
    assert "provider indisponivel" in payload
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
