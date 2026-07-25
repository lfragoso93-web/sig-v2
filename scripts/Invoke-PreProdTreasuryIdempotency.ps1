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

$OperationId = Get-Date -Format 'yyyyMMdd-HHmmss'
$OperationDirectory = Join-Path $ArtifactRoot "treasury-idempotency-$OperationId"
New-Item -ItemType Directory -Path $OperationDirectory -Force | Out-Null

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
        [string]$EvidencePath
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

    & docker @DockerArguments | Tee-Object -FilePath $EvidencePath
    $SeedExitCode = $LASTEXITCODE
    if ($null -eq $SeedExitCode) {
        throw 'docker did not return an exit code for the Treasury seed.'
    }
    if ($SeedExitCode -ne 0) {
        throw "Treasury seed failed with exit code $SeedExitCode."
    }
}

$FirstRunId = New-DistinctRunId -PreviousRunId ''
$FirstEvidencePath = Join-Path $OperationDirectory 'first.json'
Invoke-TreasurySeed -RunId $FirstRunId -EvidencePath $FirstEvidencePath

$SecondRunId = New-DistinctRunId -PreviousRunId $FirstRunId
$SecondEvidencePath = Join-Path $OperationDirectory 'second.json'
Invoke-TreasurySeed -RunId $SecondRunId -EvidencePath $SecondEvidencePath

$ReportPath = Join-Path $OperationDirectory 'idempotency.json'
$CompareArguments = @(
    'compose'
    'exec'
    '-T'
    'backend'
    'python'
    '-m'
    'app.cli.pre_prod_treasury_seed_idempotency'
    '--first'
    $FirstEvidencePath
    '--second'
    $SecondEvidencePath
)

& docker @CompareArguments | Tee-Object -FilePath $ReportPath
$CompareExitCode = $LASTEXITCODE
if ($null -eq $CompareExitCode) {
    throw 'docker did not return an exit code for the idempotency comparison.'
}

[ordered]@{
    operation_id = $OperationId
    commit_sha = $NormalizedCommitSha
    first_run_id = $FirstRunId
    second_run_id = $SecondRunId
    first_evidence = $FirstEvidencePath
    second_evidence = $SecondEvidencePath
    idempotency_report = $ReportPath
    exit_code = $CompareExitCode
} | ConvertTo-Json -Depth 3

exit $CompareExitCode
