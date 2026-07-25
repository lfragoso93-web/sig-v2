from __future__ import annotations

from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "Invoke-PreProdTreasuryIdempotency.ps1"
)


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_wrapper_requires_sha_bound_confirmation_before_docker() -> None:
    script = _script()

    confirmation = 'EXECUTE-TREASURY-IDEMPOTENCY:$NormalizedCommitSha'
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


def test_wrapper_preserves_safe_powershell_execution() -> None:
    script = _script()

    assert "Set-StrictMode -Version Latest" in script
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "Invoke-Expression" not in script
    assert "sh -lc" not in script
    assert "python -c" not in script
    assert "exit $CompareExitCode" in script
