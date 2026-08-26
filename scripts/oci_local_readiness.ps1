param(
    [switch]$SkipSourcePackage
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error "[oci-local-readiness] $Message"
    exit 1
}

function Ok {
    param([string]$Message)
    Write-Host "[oci-local-readiness] OK: $Message"
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    Fail "could not read git branch"
}
if ($branch -ne "stable-15jun") {
    Fail "branch must be stable-15jun, got $branch"
}
Ok "branch is stable-15jun"

$trackedChanges = git status --porcelain --untracked-files=no
if ($LASTEXITCODE -ne 0) {
    Fail "could not read tracked git status"
}
if ($trackedChanges) {
    Fail "tracked files must be clean"
}
Ok "tracked files are clean"

$trackedFiles = git ls-files
if ($LASTEXITCODE -ne 0) {
    Fail "could not list tracked files"
}

$forbiddenTrackedPatterns = @(
    '^\.env$',
    '^.*\.env\.local$',
    '^artifacts/pre-prod-rebuild/',
    '^artifacts/oci-source-package/',
    '^.*node_modules/',
    '^.*\.pem$',
    '^.*\.key$',
    '^.*terraform.*\.tfstate'
)

foreach ($pattern in $forbiddenTrackedPatterns) {
    $matches = @($trackedFiles | Where-Object { $_ -match $pattern })
    if ($matches.Count -gt 0) {
        Fail "forbidden tracked file matched ${pattern}: $($matches[0])"
    }
}
Ok "no forbidden sensitive/runtime artifacts are tracked"

powershell -ExecutionPolicy Bypass -File scripts\oci_compose_preflight.ps1
if ($LASTEXITCODE -ne 0) {
    Fail "OCI compose preflight failed"
}
Ok "OCI compose preflight passed"

if (-not $SkipSourcePackage) {
    powershell -ExecutionPolicy Bypass -File scripts\oci_source_package.ps1
    if ($LASTEXITCODE -ne 0) {
        Fail "OCI source package failed"
    }
    Ok "OCI source package generated"
}

Write-Host "[oci-local-readiness] local readiness checks passed"

