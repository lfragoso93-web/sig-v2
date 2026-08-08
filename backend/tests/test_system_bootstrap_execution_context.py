from datetime import UTC, datetime

import pytest

from app.services.system_bootstrap_execution_context import (
    BOOTSTRAP_BRANCH,
    BOOTSTRAP_COMMIT_SHA_ENV,
    SystemBootstrapContextError,
    build_system_bootstrap_execution_context,
)


VALID_SHA = "a" * 40


def test_bootstrap_context_uses_explicit_sha_and_canonical_branch(monkeypatch) -> None:
    monkeypatch.delenv(BOOTSTRAP_COMMIT_SHA_ENV, raising=False)
    context = build_system_bootstrap_execution_context(
        commit_sha=VALID_SHA,
        now=datetime(2026, 8, 8, 1, 2, 3, tzinfo=UTC),
    )

    assert context.run_id == "20260808-010203"
    assert context.branch == BOOTSTRAP_BRANCH == "stable-15jun"
    assert context.commit_sha == VALID_SHA
    assert not hasattr(context, "history_start_date")


def test_bootstrap_context_requires_full_sha(monkeypatch) -> None:
    monkeypatch.delenv(BOOTSTRAP_COMMIT_SHA_ENV, raising=False)
    with pytest.raises(SystemBootstrapContextError):
        build_system_bootstrap_execution_context(commit_sha="deadbeef")


def test_bootstrap_context_can_read_sha_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(BOOTSTRAP_COMMIT_SHA_ENV, VALID_SHA)
    context = build_system_bootstrap_execution_context(
        now=datetime(2026, 8, 8, 1, 2, 3, tzinfo=UTC),
    )
    assert context.commit_sha == VALID_SHA
