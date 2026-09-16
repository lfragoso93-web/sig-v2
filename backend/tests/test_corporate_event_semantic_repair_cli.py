from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.cli import corporate_event_semantic_repair as cli


def _arguments(*, execute: bool = False) -> Namespace:
    return Namespace(event_id=[370, 371], execute=execute)


class _FakeSession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def session(monkeypatch) -> _FakeSession:
    fake_session = _FakeSession()
    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: fake_session)
    return fake_session


def _report(*, dry_run: bool, writes: int) -> SimpleNamespace:
    return SimpleNamespace(
        to_dict=lambda: {
            "schema_version": "corporate-event-semantic-repair.v1",
            "dry_run": dry_run,
            "database_writes_executed": writes,
            "total_candidates": 2,
            "candidates": [],
        }
    )


@pytest.mark.asyncio
async def test_cli_defaults_to_dry_run_and_rolls_back(
    monkeypatch,
    capsys,
    session: _FakeSession,
) -> None:
    dry_run = AsyncMock(return_value=_report(dry_run=True, writes=0))
    execute = AsyncMock()
    monkeypatch.setattr(cli, "build_corporate_event_semantic_repair_dry_run", dry_run)
    monkeypatch.setattr(cli, "execute_corporate_event_semantic_repair", execute)

    exit_code = await cli._main(_arguments())

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"dry_run": true' in payload
    assert '"database_writes_executed": 0' in payload
    dry_run.assert_awaited_once_with(session, event_ids=(370, 371))
    execute.assert_not_awaited()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_cli_execute_requires_explicit_flag_and_commits(
    monkeypatch,
    capsys,
    session: _FakeSession,
) -> None:
    dry_run = AsyncMock()
    execute = AsyncMock(return_value=_report(dry_run=False, writes=2))
    monkeypatch.setattr(cli, "build_corporate_event_semantic_repair_dry_run", dry_run)
    monkeypatch.setattr(cli, "execute_corporate_event_semantic_repair", execute)

    exit_code = await cli._main(_arguments(execute=True))

    assert exit_code == 0
    payload = capsys.readouterr().out
    assert '"dry_run": false' in payload
    assert '"database_writes_executed": 2' in payload
    dry_run.assert_not_awaited()
    execute.assert_awaited_once_with(session, event_ids=(370, 371))
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
