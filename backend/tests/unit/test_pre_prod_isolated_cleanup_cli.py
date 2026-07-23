from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import pre_prod_isolated_cleanup as cli
from app.services.pre_prod_isolated_cleanup_contract import (
    APPROVED_BRANCH,
    APPROVED_PLAN_MODE,
    APPROVED_PLAN_SCHEMA_VERSION,
    REQUIRED_ISOLATION_MARKER,
    canonical_json_sha256,
)
from app.services.pre_prod_isolated_cleanup_executor import (
    IsolatedCleanupCountMismatchError,
)

RUN_ID = "20260723-190000"
COMMIT_SHA = "a" * 40
SOURCE_URL = "postgresql://source-user:secret@source-db:5432/sgi_pre_prod"
TARGET_URL = "postgresql://target-user:secret@isolated-db:5432/sgi_cleanup_isolated"


def _plan_payload() -> dict[str, object]:
    return {
        "schema_version": APPROVED_PLAN_SCHEMA_VERSION,
        "mode": APPROVED_PLAN_MODE,
        "run_id": RUN_ID,
        "branch": APPROVED_BRANCH,
        "commit_sha": COMMIT_SHA,
        "cleanup_order": ["transactions"],
        "tables": [
            {
                "name": "transactions",
                "expected_rows_before": 2,
            }
        ],
        "blockers": [],
        "safety": {
            "plan_only": True,
            "database_writes_executed": 0,
            "cleanup_executed": False,
            "rebuild_executed": False,
        },
    }


def _write_plan(tmp_path: Path) -> tuple[Path, str]:
    payload = _plan_payload()
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path, canonical_json_sha256(payload)


def _arguments(tmp_path: Path, **changes: object) -> argparse.Namespace:
    plan_path, checksum = _write_plan(tmp_path)
    values: dict[str, object] = {
        "plan": plan_path,
        "artifact_root": tmp_path / "artifacts",
        "branch": APPROVED_BRANCH,
        "commit_sha": COMMIT_SHA,
        "source_database_url": SOURCE_URL,
        "target_database_url": TARGET_URL,
        "target_isolation_marker": REQUIRED_ISOLATION_MARKER,
        "confirmation": (
            f"CLEANUP {RUN_ID} ON sgi_cleanup_isolated "
            f"AT {COMMIT_SHA} WITH {checksum}"
        ),
    }
    values.update(changes)
    return argparse.Namespace(**values)


class _ConnectionContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _FakeEngine:
    def __init__(self) -> None:
        self.disposed = False

    def connect(self) -> _ConnectionContext:
        return _ConnectionContext()

    def dispose(self) -> None:
        self.disposed = True


def test_invalid_utf8_or_json_returns_input_exit_code(tmp_path: Path) -> None:
    arguments = _arguments(tmp_path)
    arguments.plan.write_text("not-json", encoding="utf-8")
    called = False

    def engine_factory(_: str) -> _FakeEngine:
        nonlocal called
        called = True
        return _FakeEngine()

    assert cli.run(
        arguments,
        engine_factory=engine_factory,
    ) == cli.CleanupExitCode.INVALID_INPUT
    assert called is False


def test_branch_mismatch_aborts_before_engine_creation(tmp_path: Path) -> None:
    called = False

    def engine_factory(_: str) -> _FakeEngine:
        nonlocal called
        called = True
        return _FakeEngine()

    exit_code = cli.run(
        _arguments(tmp_path, branch="main"),
        engine_factory=engine_factory,
    )

    assert exit_code == cli.CleanupExitCode.IDENTITY_MISMATCH
    assert called is False


def test_unmarked_target_aborts_before_engine_creation(tmp_path: Path) -> None:
    called = False

    def engine_factory(_: str) -> _FakeEngine:
        nonlocal called
        called = True
        return _FakeEngine()

    exit_code = cli.run(
        _arguments(tmp_path, target_isolation_marker="missing"),
        engine_factory=engine_factory,
    )

    assert exit_code == cli.CleanupExitCode.INVALID_TARGET
    assert called is False


def test_source_equal_target_is_rejected(tmp_path: Path) -> None:
    arguments = _arguments(
        tmp_path,
        source_database_url=TARGET_URL,
    )

    assert cli.run(arguments) == cli.CleanupExitCode.INVALID_TARGET


def test_invalid_confirmation_aborts_before_engine_creation(tmp_path: Path) -> None:
    called = False

    def engine_factory(_: str) -> _FakeEngine:
        nonlocal called
        called = True
        return _FakeEngine()

    exit_code = cli.run(
        _arguments(tmp_path, confirmation="yes"),
        engine_factory=engine_factory,
    )

    assert exit_code == cli.CleanupExitCode.INVALID_CONFIRMATION
    assert called is False


def test_count_mismatch_maps_to_plan_divergence_and_disposes_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = _FakeEngine()

    def fail_count(**_: object) -> object:
        raise IsolatedCleanupCountMismatchError("rows differ")

    monkeypatch.setattr(cli, "execute_isolated_cleanup", fail_count)

    exit_code = cli.run(
        _arguments(tmp_path),
        engine_factory=lambda _: engine,
    )

    assert exit_code == cli.CleanupExitCode.PLAN_DIVERGENCE
    assert engine.disposed is True


def test_success_delegates_execution_and_publication_without_exposing_urls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    engine = _FakeEngine()
    destination = tmp_path / "artifacts" / RUN_ID / "cleanup" / "execution.json"
    captured: dict[str, object] = {}

    def execute(**kwargs: object) -> object:
        captured["authorization"] = kwargs["authorization"]
        return SimpleNamespace(
            run_id=RUN_ID,
            target_database="isolated-db:5432/sgi_cleanup_isolated",
            plan_sha256=canonical_json_sha256(_plan_payload()),
            lock_acquired=True,
            committed=True,
            tables=(),
            rows_before=0,
            rows_deleted=0,
        )

    def build(**kwargs: object) -> object:
        captured["result"] = kwargs["result"]
        return SimpleNamespace(run_id=RUN_ID)

    def publish(**_: object) -> Path:
        return destination

    monkeypatch.setattr(cli, "execute_isolated_cleanup", execute)
    monkeypatch.setattr(cli, "build_execution_report", build)
    monkeypatch.setattr(cli, "publish_execution_report", publish)

    exit_code = cli.run(
        _arguments(tmp_path),
        engine_factory=lambda _: engine,
    )

    output = capsys.readouterr().out
    assert exit_code == cli.CleanupExitCode.SUCCESS
    assert engine.disposed is True
    assert str(destination) in output
    assert "source-user" not in output
    assert "target-user" not in output
    assert "secret" not in output
    authorization = captured["authorization"]
    assert authorization.target.redacted_label == "isolated-db:5432/sgi_cleanup_isolated"
