from __future__ import annotations

import pytest

from app.cli.pre_prod_backup import (
    _validate_runtime_branch,
    _validate_runtime_commit_sha,
)
from app.services.pre_prod_backup_service import BackupError
from app.core.config import settings


VALID_SHA = "1e7c3fca6e6acaea19a75c1197f036a1f1021199"
OTHER_SHA = "f93f5a2eff0ef2c1f797209577af8d2934d8c9b0"


@pytest.mark.parametrize(
    ("environment", "runtime_branch", "requested_branch"),
    [
        ("production", "main", "main"),
        ("development", "stable-15jun", "stable-15jun"),
    ],
)
def test_backup_cli_accepts_branch_for_runtime_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    runtime_branch: str,
    requested_branch: str,
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "APP_BRANCH", runtime_branch)

    _validate_runtime_branch(requested_branch)


@pytest.mark.parametrize(
    ("environment", "runtime_branch", "requested_branch"),
    [
        ("production", "main", "stable-15jun"),
        ("development", "stable-15jun", "main"),
        ("production", "stable-15jun", "main"),
    ],
)
def test_backup_cli_rejects_branch_outside_runtime_contract(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    runtime_branch: str,
    requested_branch: str,
) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", environment)
    monkeypatch.setattr(settings, "APP_BRANCH", runtime_branch)

    with pytest.raises(BackupError):
        _validate_runtime_branch(requested_branch)


def test_backup_cli_accepts_matching_runtime_commit_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_COMMIT_SHA", VALID_SHA)

    _validate_runtime_commit_sha(VALID_SHA)


@pytest.mark.parametrize("runtime_sha", ["", "unknown"])
def test_backup_cli_rejects_missing_runtime_commit_sha(
    monkeypatch: pytest.MonkeyPatch,
    runtime_sha: str,
) -> None:
    monkeypatch.setenv("APP_COMMIT_SHA", runtime_sha)

    with pytest.raises(BackupError, match="APP_COMMIT_SHA do runtime"):
        _validate_runtime_commit_sha(VALID_SHA)


def test_backup_cli_rejects_mismatched_runtime_commit_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_COMMIT_SHA", OTHER_SHA)

    with pytest.raises(BackupError, match="diverge do commit informado"):
        _validate_runtime_commit_sha(VALID_SHA)
