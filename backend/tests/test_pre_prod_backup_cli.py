from __future__ import annotations

import pytest

from app.cli.pre_prod_backup import _validate_runtime_commit_sha
from app.services.pre_prod_backup_service import BackupError


VALID_SHA = "1e7c3fca6e6acaea19a75c1197f036a1f1021199"
OTHER_SHA = "f93f5a2eff0ef2c1f797209577af8d2934d8c9b0"


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
