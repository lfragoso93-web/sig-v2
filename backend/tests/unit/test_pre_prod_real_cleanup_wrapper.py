from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPOSITORY_ROOT / "scripts" / "Invoke-PreProdRealCleanup.ps1"


def _wrapper_source() -> str:
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
