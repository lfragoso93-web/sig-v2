[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$CommitSha,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Confirmation,

    [ValidateNotNullOrEmpty()]
    [string]$ArtifactRoot = 'artifacts/pre-prod-rebuild'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$NormalizedCommitSha = $CommitSha.ToLowerInvariant()
$ExpectedConfirmation = "EXECUTE-TREASURY-IDEMPOTENCY:$NormalizedCommitSha"
if ($Confirmation -cne $ExpectedConfirmation) {
    throw "Confirmation must be exactly '$ExpectedConfirmation'."
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
    -not $NormalizedArtifactRoot.StartsWith('artifacts/', [System.StringComparison]::Ordinal)
) {
    throw 'ArtifactRoot must be inside the mounted artifacts directory.'
}

$OperationId = Get-Date -Format 'yyyyMMdd-HHmmss'
$OperationRelativeDirectory = "$NormalizedArtifactRoot/treasury-idempotency-$OperationId"
$OperationHostDirectory = $OperationRelativeDirectory.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
$OperationContainerDirectory = "/app/$OperationRelativeDirectory"
New-Item -ItemType Directory -Path $OperationHostDirectory -Force | Out-Null

function Write-Utf8Lines {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$Lines,

        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $Text = ($Lines | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
    [System.IO.File]::WriteAllText(
        $Path,
        $Text + [Environment]::NewLine,
        [System.Text.UTF8Encoding]::new($false)
    )
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

function Invoke-TreasurySeed {
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
        'backend'
        'python'
        '-m'
        'app.cli.pre_prod_treasury_seed'
        '--run-id'
        $RunId
        '--branch'
        'stable-15jun'
        '--commit-sha'
        $NormalizedCommitSha
    )

    $SeedOutput = @(& docker @DockerArguments)
    $SeedExitCode = $LASTEXITCODE
    $SeedOutput | ForEach-Object { Write-Output $_ }
    Write-Utf8Lines -Lines $SeedOutput -Path $EvidenceHostPath
    if ($null -eq $SeedExitCode) {
        throw 'docker did not return an exit code for the Treasury seed.'
    }
    if ($SeedExitCode -ne 0) {
        throw "Treasury seed failed with exit code $SeedExitCode."
    }
}

$FirstRunId = New-DistinctRunId -PreviousRunId ''
$FirstEvidenceHostPath = Join-Path $OperationHostDirectory 'first.json'
$FirstEvidenceContainerPath = "$OperationContainerDirectory/first.json"
Invoke-TreasurySeed -RunId $FirstRunId -EvidenceHostPath $FirstEvidenceHostPath

$SecondRunId = New-DistinctRunId -PreviousRunId $FirstRunId
$SecondEvidenceHostPath = Join-Path $OperationHostDirectory 'second.json'
$SecondEvidenceContainerPath = "$OperationContainerDirectory/second.json"
Invoke-TreasurySeed -RunId $SecondRunId -EvidenceHostPath $SecondEvidenceHostPath

$ReportHostPath = Join-Path $OperationHostDirectory 'idempotency.json'
$CompareArguments = @(
    'compose'
    'exec'
    '-T'
    'backend'
    'python'
    '-m'
    'app.cli.pre_prod_treasury_seed_idempotency'
    '--first'
    $FirstEvidenceContainerPath
    '--second'
    $SecondEvidenceContainerPath
)

$CompareOutput = @(& docker @CompareArguments)
$CompareExitCode = $LASTEXITCODE
$CompareOutput | ForEach-Object { Write-Output $_ }
Write-Utf8Lines -Lines $CompareOutput -Path $ReportHostPath
if ($null -eq $CompareExitCode) {
    throw 'docker did not return an exit code for the idempotency comparison.'
}

[ordered]@{
    operation_id = $OperationId
    commit_sha = $NormalizedCommitSha
    first_run_id = $FirstRunId
    second_run_id = $SecondRunId
    first_evidence = $FirstEvidenceHostPath
    second_evidence = $SecondEvidenceHostPath
    idempotency_report = $ReportHostPath
    exit_code = $CompareExitCode
} | ConvertTo-Json -Depth 3

exit $CompareExitCode
