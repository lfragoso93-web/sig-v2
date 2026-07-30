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

$RuntimeCommitSha = (& docker compose exec -T backend printenv APP_COMMIT_SHA).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to read APP_COMMIT_SHA from the backend container.'
}
if ($RuntimeCommitSha -cne $NormalizedCommitSha) {
    throw (
        "Backend container commit mismatch: expected " +
        "'$NormalizedCommitSha', found '$RuntimeCommitSha'."
    )
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
