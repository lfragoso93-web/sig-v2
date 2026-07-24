[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PlanPath,

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

$DatabaseUrl = $env:PRE_PROD_SYNC_DATABASE_URL
if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    throw 'PRE_PROD_SYNC_DATABASE_URL must contain the synchronous PostgreSQL URL.'
}

$DockerArguments = @(
    'compose'
    'exec'
    '-T'
    'backend'
    'python'
    '-m'
    'app.cli.pre_prod_isolated_cleanup'
    '--plan'
    $PlanPath
    '--artifact-root'
    $ArtifactRoot
    '--branch'
    'stable-15jun'
    '--commit-sha'
    $CommitSha.ToLowerInvariant()
    '--source-database-url'
    $DatabaseUrl
    '--target-database-url'
    $DatabaseUrl
    '--target-isolation-marker'
    'sgi-pre-prod-real'
    '--confirmation'
    $Confirmation
)

& docker @DockerArguments
$CleanupExitCode = $LASTEXITCODE

if ($null -eq $CleanupExitCode) {
    throw 'docker did not return an exit code.'
}

exit $CleanupExitCode
