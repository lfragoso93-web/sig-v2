param(
    [string]$OutputDirectory = "artifacts\oci-source-package"
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error "[oci-source-package] $Message"
    exit 1
}

function Ok {
    param([string]$Message)
    Write-Host "[oci-source-package] OK: $Message"
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($LASTEXITCODE -ne 0) {
    Fail "could not read git branch"
}
if ($branch -ne "stable-15jun") {
    Fail "branch must be stable-15jun, got $branch"
}
Ok "branch is stable-15jun"

$status = git status --porcelain
if ($LASTEXITCODE -ne 0) {
    Fail "could not read git status"
}
if ($status) {
    Fail "working tree must be clean before packaging"
}
Ok "working tree is clean"

$commit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $commit -notmatch "^[0-9a-f]{40}$") {
    Fail "could not read full commit SHA"
}
Ok "commit=$commit"

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$tarPath = Join-Path $OutputDirectory "sgi-v2-$commit.tar"
$manifestPath = Join-Path $OutputDirectory "sgi-v2-$commit-manifest.txt"

git archive --format=tar --output $tarPath HEAD
if ($LASTEXITCODE -ne 0) {
    Fail "git archive failed"
}
Ok "archive created: $tarPath"

$tarHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $tarPath).Hash.ToLowerInvariant()
$trackedCount = (git ls-tree -r --name-only HEAD | Measure-Object).Count

$manifest = @(
    "name=sgi-v2",
    "branch=$branch",
    "commit=$commit",
    "archive=$(Split-Path -Leaf $tarPath)",
    "sha256=$tarHash",
    "tracked_files=$trackedCount",
    "created_utc=$((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))"
)
$manifest | Set-Content -LiteralPath $manifestPath -Encoding utf8
Ok "manifest created: $manifestPath"

$listing = tar -tf $tarPath
if ($LASTEXITCODE -ne 0) {
    Fail "could not list generated tar archive"
}
$listingText = ($listing -join "`n")
if ($listingText -match "(^|/)\.env($|\n)") {
    Fail "archive contains .env"
}
if ($listingText -match "(^|/)node_modules/") {
    Fail "archive contains node_modules"
}
if ($listingText -match "(^|/)\.git/") {
    Fail "archive contains .git"
}
if ($listingText -match "^artifacts/pre-prod-rebuild/") {
    Fail "archive contains backup artifacts"
}
Ok "archive excludes .env, .git, node_modules, and backup artifacts"

Write-Host "[oci-source-package] package ready"
Write-Host "[oci-source-package] archive=$tarPath"
Write-Host "[oci-source-package] manifest=$manifestPath"
