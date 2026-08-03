from __future__ import annotations

from pathlib import Path

import pytest


SCRIPT_NAME = "Invoke-PreProdRealCleanup.ps1"


def _find_wrapper() -> Path | None:
    test_path = Path(__file__).resolve()
    for ancestor in (test_path.parent, *test_path.parents):
        candidate = ancestor / "scripts" / SCRIPT_NAME
        if candidate.is_file():
            return candidate
    return None


WRAPPER = _find_wrapper()
pytestmark = pytest.mark.skipif(
    WRAPPER is None,
    reason=(
        "wrapper PowerShell não está incluído nesta imagem backend; "
        "execute esta suíte no checkout completo do repositório"
    ),
)


def _wrapper_source() -> str:
    assert WRAPPER is not None
    return WRAPPER.read_text(encoding="utf-8")


def test_wrapper_delegates_only_to_the_approved_real_cleanup_profile() -> None:
    source = _wrapper_source()

    assert "'app.cli.pre_prod_isolated_cleanup'" in source
    assert "'stable-15jun'" in source
    assert "'sgi-pre-prod-real'" in source
    assert source.count("$DatabaseUrl") == 4
    assert "--rehearsal-fail-after-table" not in source


def test_wrapper_preserves_argument_boundaries_and_cli_exit_code() -> None:
    source = _wrapper_source()

    assert "$DockerArguments = @(" in source
    assert "& docker @DockerArguments" in source
    assert "$CleanupExitCode = $LASTEXITCODE" in source
    assert "exit $CleanupExitCode" in source

    forbidden_constructs = (
        "Invoke-Expression",
        "python -c",
        "sh -lc",
        "Start-Process",
    )
    assert not any(construct in source for construct in forbidden_constructs)


def test_wrapper_requires_database_url_from_environment() -> None:
    source = _wrapper_source()

    assert "$env:PRE_PROD_SYNC_DATABASE_URL" in source
    assert "PRE_PROD_SYNC_DATABASE_URL must contain" in source
