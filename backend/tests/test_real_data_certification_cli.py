"""Safety-boundary tests for the real-data certification CLI."""

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.cli import real_data_certification as cli
from app.services.real_data_certification_contract import (
    RealDataCertificationAction,
    RealDataCertificationValidationError,
)


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
    fake = _FakeSession()
    monkeypatch.setattr(cli, "AsyncSessionLocal", lambda: fake)
    return fake


@pytest.fixture
def evidence_file(tmp_path: Path) -> Path:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps({"status": "GO"}), encoding="utf-8")
    return path


def _arguments(
    evidence_file: Path,
    *,
    execute: bool = False,
    confirmation: str | None = None,
) -> Namespace:
    return Namespace(
        action="promote",
        environment="local-canonical",
        branch="stable-15jun",
        commit_sha="a" * 40,
        dataset_reference="dataset:2026-10-06",
        alembic_revision="20261005_real_data_certification",
        gate_issue_reference="#227",
        pull_request_reference="#362",
        evidence_file=evidence_file,
        actor="operator@example.test",
        reason="formal decision",
        execute=execute,
        confirmation=confirmation,
    )


def _plan():
    return SimpleNamespace(
        event_key="event-1",
        confirmation="PROMOTE exact confirmation",
        to_dict=lambda: {
            "event_key": "event-1",
            "confirmation": "PROMOTE exact confirmation",
            "dry_run": True,
            "database_writes_executed": 0,
        },
    )


@pytest.mark.asyncio
async def test_cli_defaults_to_dry_run_and_rolls_back(
    monkeypatch,
    capsys,
    session: _FakeSession,
    evidence_file: Path,
) -> None:
    prepare = AsyncMock(return_value=_plan())
    execute = AsyncMock()
    monkeypatch.setattr(cli, "prepare_real_data_certification_plan", prepare)
    monkeypatch.setattr(cli, "execute_real_data_certification_plan", execute)

    exit_code = await cli._main(_arguments(evidence_file))

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry-run"
    assert payload["database_writes_executed"] == 0
    assert payload["transaction_committed"] is False
    assert payload["plan"]["confirmation"] == "PROMOTE exact confirmation"
    prepare.assert_awaited_once()
    execute.assert_not_awaited()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_without_confirmation_stops_before_session_creation(
    monkeypatch,
    evidence_file: Path,
) -> None:
    session_factory = AsyncMock()
    monkeypatch.setattr(cli, "AsyncSessionLocal", session_factory)

    with pytest.raises(RealDataCertificationValidationError, match="requires"):
        await cli._main(_arguments(evidence_file, execute=True))

    session_factory.assert_not_called()


@pytest.mark.asyncio
async def test_execute_commits_only_after_executor_returns(
    monkeypatch,
    capsys,
    session: _FakeSession,
    evidence_file: Path,
) -> None:
    prepare = AsyncMock(return_value=_plan())
    result = SimpleNamespace(
        database_writes_executed=1,
        transaction_committed=False,
    )
    committed = SimpleNamespace(
        database_writes_executed=1,
        transaction_committed=True,
        to_dict=lambda: {
            "database_writes_executed": 1,
            "transaction_committed": True,
        },
    )
    execute = AsyncMock(return_value=result)
    mark_committed = MagicMock(return_value=committed)
    monkeypatch.setattr(cli, "prepare_real_data_certification_plan", prepare)
    monkeypatch.setattr(cli, "execute_real_data_certification_plan", execute)
    monkeypatch.setattr(cli, "mark_certification_result_committed", mark_committed)

    exit_code = await cli._main(
        _arguments(
            evidence_file,
            execute=True,
            confirmation="PROMOTE exact confirmation",
        )
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "execute"
    assert payload["database_writes_executed"] == 1
    assert payload["transaction_committed"] is True
    execute.assert_awaited_once_with(
        session,
        plan=prepare.return_value,
        confirmation="PROMOTE exact confirmation",
    )
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_executor_failure_rolls_back_and_never_commits(
    monkeypatch,
    session: _FakeSession,
    evidence_file: Path,
) -> None:
    monkeypatch.setattr(
        cli,
        "prepare_real_data_certification_plan",
        AsyncMock(return_value=_plan()),
    )
    monkeypatch.setattr(
        cli,
        "execute_real_data_certification_plan",
        AsyncMock(side_effect=RuntimeError("stale")),
    )

    with pytest.raises(RuntimeError, match="stale"):
        await cli._main(
            _arguments(
                evidence_file,
                execute=True,
                confirmation="PROMOTE exact confirmation",
            )
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_parser_requires_identity_evidence_actor_and_reason() -> None:
    parser = cli._parser()
    required_destinations = {
        action.dest
        for action in parser._actions
        if getattr(action, "required", False)
    }
    assert {
        "action",
        "environment",
        "branch",
        "commit_sha",
        "dataset_reference",
        "alembic_revision",
        "gate_issue_reference",
        "pull_request_reference",
        "evidence_file",
        "actor",
        "reason",
    } <= required_destinations
    assert parser.get_default("execute") is False


def test_action_mapping_is_explicit() -> None:
    assert RealDataCertificationAction("PROMOTE") is RealDataCertificationAction.PROMOTE
