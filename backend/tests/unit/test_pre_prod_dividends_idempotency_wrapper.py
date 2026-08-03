from __future__ import annotations

from pathlib import Path

import pytest

SCRIPT_NAME = "Invoke-PreProdDividendsIdempotency.ps1"


def _find_repository_root() -> Path | None:
    test_path = Path(__file__).resolve()
    for ancestor in (test_path.parent, *test_path.parents):
        script = ancestor / "scripts" / SCRIPT_NAME
        dockerfile = ancestor / "backend" / "Dockerfile"
        compose = ancestor / "docker-compose.yml"
        if script.is_file() and dockerfile.is_file() and compose.is_file():
            return ancestor
    return None


REPOSITORY_ROOT = _find_repository_root()
pytestmark = pytest.mark.skipif(
    REPOSITORY_ROOT is None,
    reason=(
        "wrappers e artefatos de raiz não estão incluídos nesta imagem backend; "
        "execute esta suíte no checkout completo do repositório"
    ),
)

SCRIPT_PATH = (
    REPOSITORY_ROOT / "scripts" / SCRIPT_NAME
    if REPOSITORY_ROOT is not None
    else Path("/nonexistent")
)
DOCKERFILE_PATH = (
    REPOSITORY_ROOT / "backend" / "Dockerfile"
    if REPOSITORY_ROOT is not None
    else Path("/nonexistent")
)
COMPOSE_PATH = (
    REPOSITORY_ROOT / "docker-compose.yml"
    if REPOSITORY_ROOT is not None
    else Path("/nonexistent")
)


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_wrapper_is_part_of_the_repository() -> None:
    assert SCRIPT_PATH.is_file()


def test_wrapper_validates_identity_window_and_confirmation_before_docker() -> None:
    script = _script()

    confirmation = "EXECUTE-DIVIDENDS-IDEMPOTENCY:$NormalizedCommitSha"
    assert confirmation in script
    assert script.index("$ExpectedConfirmation") < script.index("& docker")
    assert script.index("$ParsedStartDate -gt $ParsedEndDate") < script.index(
        "& docker"
    )
    assert "Current branch must be exactly 'stable-15jun'." in script
    assert "Current HEAD does not match CommitSha." in script


def test_wrapper_runs_seed_twice_and_compares_offline() -> None:
    script = _script()

    assert script.count("Invoke-DividendsSeed -RunId") == 2
    assert "New-DistinctRunId -PreviousRunId $FirstRunId" in script
    assert "app.cli.pre_prod_dividends_seed'" in script
    assert "app.cli.pre_prod_dividends_seed_idempotency'" in script
    assert "'--start-date'\n        $StartDate" in script
    assert "'--end-date'\n        $EndDate" in script
    assert "first.json" in script
    assert "second.json" in script
    assert "idempotency.json" in script


def test_wrapper_maps_evidence_paths_to_mounted_artifacts() -> None:
    script = _script()

    assert "ArtifactRoot must be a repository-relative path under artifacts." in script
    assert "ArtifactRoot must be inside the mounted artifacts directory." in script
    assert '$OperationContainerDirectory = "/app/$OperationRelativeDirectory"' in script
    assert "$FirstEvidenceContainerPath" in script
    assert "$SecondEvidenceContainerPath" in script


def test_wrapper_preserves_three_evidences_atomically_as_utf8() -> None:
    script = _script()

    assert "function Write-Utf8LinesAtomically" in script
    assert script.count("Write-Utf8LinesAtomically -Lines") == 2
    assert script.count("Invoke-DividendsSeed -RunId") == 2
    assert "[System.IO.File]::WriteAllText(" in script
    assert "[System.Text.UTF8Encoding]::new($false)" in script
    assert 'Move-Item -LiteralPath $TemporaryPath -Destination $Path' in script
    assert "Tee-Object -FilePath" not in script


def test_wrapper_preserves_native_exit_codes_and_safe_execution() -> None:
    script = _script()

    assert script.index("$SeedExitCode = $LASTEXITCODE") < script.index(
        "$SeedOutput | ForEach-Object"
    )
    assert script.index("$CompareExitCode = $LASTEXITCODE") < script.index(
        "$CompareOutput | ForEach-Object"
    )
    assert "Set-StrictMode -Version Latest" in script
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "Invoke-Expression" not in script
    assert "sh -lc" not in script
    assert "python -c" not in script
    assert "exit $CompareExitCode" in script


def test_backend_image_embeds_declared_commit_identity() -> None:
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    compose = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "ARG APP_COMMIT_SHA=unknown" in dockerfile
    assert "ENV APP_COMMIT_SHA=$APP_COMMIT_SHA" in dockerfile
    assert "LABEL org.opencontainers.image.revision=$APP_COMMIT_SHA" in dockerfile
    assert "APP_COMMIT_SHA: ${APP_COMMIT_SHA:-unknown}" in compose


def test_wrapper_rejects_stale_runtime_before_creating_evidence() -> None:
    script = _script()

    runtime_probe = "docker compose exec -T backend printenv APP_COMMIT_SHA"
    mismatch = "Backend container commit mismatch: expected"
    evidence_creation = "New-Item -ItemType Directory"

    assert runtime_probe in script
    assert "Unable to read APP_COMMIT_SHA from the backend container." in script
    assert mismatch in script
    assert script.index(runtime_probe) < script.index(evidence_creation)
    assert script.index(mismatch) < script.index(evidence_creation)
    assert script.index("$RuntimeCommitExitCode = $LASTEXITCODE") < script.index(
        "$RuntimeCommitSha = ([string]$RuntimeCommitOutput)"
    )
