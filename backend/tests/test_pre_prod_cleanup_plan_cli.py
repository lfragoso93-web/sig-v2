from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.cli import pre_prod_cleanup_plan as cli
from app.services.pre_prod_cleanup_execution_service import (
    CleanupExecutionValidationError,
)


def _arguments(tmp_path: Path, **overrides) -> argparse.Namespace:  # type: ignore[no-untyped-def]
    values = {
        "artifact_root": tmp_path,
        "run_id": "run-1",
        "branch": "stable-15jun",
        "commit_sha": "a" * 40,
        "cleanup_impact_path": None,
        "manifest_path": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_validate_identity_requires_branch(tmp_path: Path) -> None:
    with pytest.raises(cli.CleanupPlanIdentityError, match="branch"):
        cli._validate_identity(_arguments(tmp_path, branch=None))


def test_validate_identity_requires_commit_sha(tmp_path: Path) -> None:
    with pytest.raises(cli.CleanupPlanIdentityError, match="commit-sha"):
        cli._validate_identity(_arguments(tmp_path, commit_sha=None))


def test_resolve_paths_uses_run_directory_defaults(tmp_path: Path) -> None:
    run_directory, cleanup_path, manifest_path = cli._resolve_paths(
        _arguments(tmp_path)
    )

    assert run_directory == tmp_path / "run-1"
    assert cleanup_path == run_directory / "cleanup-impact.json"
    assert manifest_path == run_directory / "export" / "manifest.json"


def test_main_builds_and_publishes_plan_without_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    plan = SimpleNamespace(
        schema_version="pre-prod-cleanup-execution.v1",
        run_id="run-1",
        to_dict=lambda: {
            "schema_version": "pre-prod-cleanup-execution.v1",
            "safety": {
                "plan_only": True,
                "database_writes_executed": 0,
                "cleanup_executed": False,
            },
        },
    )
    captured: dict[str, object] = {}

    def fake_build(**kwargs):  # type: ignore[no-untyped-def]
        captured["build"] = kwargs
        return plan

    def fake_publish(**kwargs):  # type: ignore[no-untyped-def]
        captured["publish"] = kwargs
        return tmp_path / "run-1" / "cleanup" / "plan.json"

    monkeypatch.setattr(cli, "build_pre_prod_cleanup_execution_plan", fake_build)
    monkeypatch.setattr(cli, "publish_pre_prod_cleanup_execution_plan", fake_publish)

    assert cli._main(_arguments(tmp_path)) == 0

    output = capsys.readouterr().out
    assert '"database_accessed": false' in output
    assert '"database_writes_executed": 0' in output
    assert '"cleanup_executed": false' in output
    assert captured["build"]["run_id"] == "run-1"  # type: ignore[index]
    assert captured["publish"]["plan"] is plan  # type: ignore[index]


@pytest.mark.parametrize(
    ("exception", "expected_code"),
    [
        (cli.CleanupPlanIdentityError("identity"), cli.IDENTITY_EXIT_CODE),
        (
            CleanupExecutionValidationError("validation"),
            cli.VALIDATION_EXIT_CODE,
        ),
        (FileExistsError("exists"), cli.ALREADY_EXISTS_EXIT_CODE),
        (RuntimeError("unexpected"), 1),
    ],
)
def test_main_entrypoint_maps_failures_to_exit_codes(
    monkeypatch: pytest.MonkeyPatch,
    exception: Exception,
    expected_code: int,
) -> None:
    monkeypatch.setattr(cli, "_arguments", lambda: argparse.Namespace())

    def fail(_arguments: argparse.Namespace) -> int:
        raise exception

    monkeypatch.setattr(cli, "_main", fail)

    with pytest.raises(SystemExit) as raised:
        cli.main()

    assert raised.value.code == expected_code
