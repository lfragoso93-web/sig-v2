from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "Invoke-PreProdTreasuryIdempotency.ps1"


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_wrapper_script_path_resolves_inside_repository() -> None:
    assert REPOSITORY_ROOT.name == "app"
    assert SCRIPT_PATH.is_file()


def test_wrapper_requires_sha_bound_confirmation_before_docker() -> None:
    script = _script()

    confirmation = "EXECUTE-TREASURY-IDEMPOTENCY:$NormalizedCommitSha"
    assert confirmation in script
    assert script.index("$ExpectedConfirmation") < script.index("& docker")
    assert "Current branch must be exactly 'stable-15jun'." in script
    assert "Current HEAD does not match CommitSha." in script


def test_wrapper_runs_seed_twice_and_compares_offline_evidence() -> None:
    script = _script()

    assert script.count("Invoke-TreasurySeed -RunId") == 2
    assert "New-DistinctRunId -PreviousRunId $FirstRunId" in script
    assert "app.cli.pre_prod_treasury_seed'" in script
    assert "app.cli.pre_prod_treasury_seed_idempotency'" in script
    assert "first.json" in script
    assert "second.json" in script
    assert "idempotency.json" in script


def test_wrapper_maps_host_artifacts_to_backend_volume() -> None:
    script = _script()

    assert "ArtifactRoot must be a repository-relative path under artifacts." in script
    assert "ArtifactRoot must be inside the mounted artifacts directory." in script
    assert '$OperationContainerDirectory = "/app/$OperationRelativeDirectory"' in script
    assert "$FirstEvidenceHostPath" in script
    assert "$FirstEvidenceContainerPath" in script
    assert "$SecondEvidenceHostPath" in script
    assert "$SecondEvidenceContainerPath" in script
    assert "'--first'\n    $FirstEvidenceContainerPath" in script
    assert "'--second'\n    $SecondEvidenceContainerPath" in script


def test_wrapper_persists_evidence_and_report_as_explicit_utf8() -> None:
    script = _script()

    assert "function Write-Utf8Lines" in script
    assert "[System.IO.File]::WriteAllText(" in script
    assert "[System.Text.UTF8Encoding]::new($false)" in script
    assert "Write-Utf8Lines -Lines $SeedOutput -Path $EvidenceHostPath" in script
    assert "Write-Utf8Lines -Lines $CompareOutput -Path $ReportHostPath" in script
    assert "Tee-Object -FilePath" not in script


def test_wrapper_preserves_native_exit_codes_before_rendering_output() -> None:
    script = _script()

    assert script.index("$SeedExitCode = $LASTEXITCODE") < script.index(
        "$SeedOutput | ForEach-Object"
    )
    assert script.index("$CompareExitCode = $LASTEXITCODE") < script.index(
        "$CompareOutput | ForEach-Object"
    )


def test_wrapper_preserves_safe_powershell_execution() -> None:
    script = _script()

    assert "Set-StrictMode -Version Latest" in script
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "Invoke-Expression" not in script
    assert "sh -lc" not in script
    assert "python -c" not in script
    assert "exit $CompareExitCode" in script
