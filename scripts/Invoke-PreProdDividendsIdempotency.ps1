[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$CommitSha,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Confirmation,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$StartDate,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{4}-\d{2}-\d{2}$')]
    [string]$EndDate,

    [ValidateNotNullOrEmpty()]
    [string]$ArtifactRoot = 'artifacts/pre-prod-rebuild'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NormalizedCommitSha = $CommitSha.ToLowerInvariant()
$ExpectedConfirmation = "EXECUTE-DIVIDENDS-IDEMPOTENCY:$NormalizedCommitSha"
if ($Confirmation -cne $ExpectedConfirmation) {
    throw "Confirmation must be exactly '$ExpectedConfirmation'."
}

$ParsedStartDate = [datetime]::MinValue
$ParsedEndDate = [datetime]::MinValue
if (
    -not [datetime]::TryParseExact(
        $StartDate,
        'yyyy-MM-dd',
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$ParsedStartDate
    ) -or
    -not [datetime]::TryParseExact(
        $EndDate,
        'yyyy-MM-dd',
        [System.Globalization.CultureInfo]::InvariantCulture,
        [System.Globalization.DateTimeStyles]::None,
        [ref]$ParsedEndDate
    )
) {
    throw 'StartDate and EndDate must be valid ISO dates.'
}
if ($ParsedStartDate -gt $ParsedEndDate) {
    throw 'StartDate must not be later than EndDate.'
}

$CurrentBranch = (& git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $CurrentBranch -cne 'stable-15jun') {
    throw "Current branch must be exactly 'stable-15jun'."
}

$CurrentCommitSha = (& git rev-parse HEAD).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $CurrentCommitSha -cne $NormalizedCommitSha) {
    throw 'Current HEAD does not match CommitSha.'
}

if ([System.IO.Path]::IsPathRooted($ArtifactRoot)) {
    throw 'ArtifactRoot must be a repository-relative path under artifacts.'
}

$NormalizedArtifactRoot = $ArtifactRoot.Replace('\', '/').TrimEnd('/')
if (
    $NormalizedArtifactRoot -ne 'artifacts' -and
    -not $NormalizedArtifactRoot.StartsWith(
        'artifacts/',
        [System.StringComparison]::Ordinal
    )
) {
    throw 'ArtifactRoot must be inside the mounted artifacts directory.'
}

$OperationId = Get-Date -Format 'yyyyMMdd-HHmmss'
$OperationRelativeDirectory = (
    "$NormalizedArtifactRoot/dividends-idempotency-$OperationId"
)
$OperationHostDirectory = $OperationRelativeDirectory.Replace(
    '/',
    [System.IO.Path]::DirectorySeparatorChar
)
$OperationContainerDirectory = "/app/$OperationRelativeDirectory"
New-Item -ItemType Directory -Path $OperationHostDirectory -Force | Out-Null

function Write-Utf8LinesAtomically {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$Lines,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        throw "Evidence already exists: $Path"
    }

    $TemporaryPath = "$Path.tmp"
    if (Test-Path -LiteralPath $TemporaryPath) {
        throw "Temporary evidence already exists: $TemporaryPath"
    }

    $Text = ($Lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    try {
        [System.IO.File]::WriteAllText(
            $TemporaryPath,
            $Text + [Environment]::NewLine,
            [System.Text.UTF8Encoding]::new($false)
        )
        Move-Item -LiteralPath $TemporaryPath -Destination $Path
    }
    finally {
        if (Test-Path -LiteralPath $TemporaryPath) {
            Remove-Item -LiteralPath $TemporaryPath -Force
        }
    }
}

function New-DistinctRunId {
    param([string]$PreviousRunId)

    do {
        $RunId = Get-Date -Format 'yyyyMMdd-HHmmss'
        if ($RunId -eq $PreviousRunId) {
            Start-Sleep -Milliseconds 250
        }
    } while ($RunId -eq $PreviousRunId)

    return $RunId
}

function Invoke-DividendsSeed {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RunId,

        [Parameter(Mandatory = $true)]
        [string]$EvidenceHostPath
    )

    $DockerArguments = @(
        'compose'
        'exec'
        '-T'
        '-e'
        'PRE_PROD_BRANCH=stable-15jun'
        '-e'
        "PRE_PROD_COMMIT_SHA=$NormalizedCommitSha"
        'backend'
        'python'
        '-m'
        'app.cli.pre_prod_dividends_seed'
        '--run-id'
        $RunId
        '--branch'
        'stable-15jun'
        '--commit-sha'
        $NormalizedCommitSha
        '--start-date'
        $StartDate
        '--end-date'
        $EndDate
    )

    $SeedOutput = @(& docker @DockerArguments)
    $SeedExitCode = $LASTEXITCODE
    $SeedOutput | ForEach-Object { Write-Output $_ }
    Write-Utf8LinesAtomically -Lines $SeedOutput -Path $EvidenceHostPath
    if ($null -eq $SeedExitCode) {
        throw 'docker did not return an exit code for the dividends seed.'
    }
    if ($SeedExitCode -ne 0) {
        throw "Dividends seed failed with exit code $SeedExitCode."
    }
}

$FirstRunId = New-DistinctRunId -PreviousRunId ''
$FirstEvidenceHostPath = Join-Path $OperationHostDirectory 'first.json'
$FirstEvidenceContainerPath = "$OperationContainerDirectory/first.json"
Invoke-DividendsSeed -RunId $FirstRunId -EvidenceHostPath $FirstEvidenceHostPath

$SecondRunId = New-DistinctRunId -PreviousRunId $FirstRunId
$SecondEvidenceHostPath = Join-Path $OperationHostDirectory 'second.json'
$SecondEvidenceContainerPath = "$OperationContainerDirectory/second.json"
Invoke-DividendsSeed -RunId $SecondRunId -EvidenceHostPath $SecondEvidenceHostPath

$ReportHostPath = Join-Path $OperationHostDirectory 'idempotency.json'
$CompareArguments = @(
    'compose'
    'exec'
    '-T'
    'backend'
    'python'
    '-m'
    'app.cli.pre_prod_dividends_seed_idempotency'
    '--first'
    $FirstEvidenceContainerPath
    '--second'
    $SecondEvidenceContainerPath
)

$CompareOutput = @(& docker @CompareArguments)
$CompareExitCode = $LASTEXITCODE
$CompareOutput | ForEach-Object { Write-Output $_ }
Write-Utf8LinesAtomically -Lines $CompareOutput -Path $ReportHostPath
if ($null -eq $CompareExitCode) {
    throw 'docker did not return an exit code for the idempotency comparison.'
}

[ordered]@{
    operation_id = $OperationId
    branch = 'stable-15jun'
    commit_sha = $NormalizedCommitSha
    start_date = $StartDate
    end_date = $EndDate
    first_run_id = $FirstRunId
    second_run_id = $SecondRunId
    first_evidence = $FirstEvidenceHostPath
    second_evidence = $SecondEvidenceHostPath
    idempotency_report = $ReportHostPath
    exit_code = $CompareExitCode
} | ConvertTo-Json -Depth 3

exit $CompareExitCode
from __future__ import annotations

from pathlib import Path

SCRIPT_NAME = "Invoke-PreProdDividendsIdempotency.ps1"
SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / SCRIPT_NAME
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
