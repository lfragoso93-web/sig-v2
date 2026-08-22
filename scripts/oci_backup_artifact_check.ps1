param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDirectory
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error "[oci-backup-artifact-check] $Message"
    exit 1
}

function Ok {
    param([string]$Message)
    Write-Host "[oci-backup-artifact-check] OK: $Message"
}

$resolved = Resolve-Path -LiteralPath $BackupDirectory -ErrorAction SilentlyContinue
if (-not $resolved) {
    Fail "backup directory not found: $BackupDirectory"
}

$backupPath = $resolved.Path
if (-not (Test-Path -LiteralPath $backupPath -PathType Container)) {
    Fail "backup path is not a directory: $backupPath"
}
Ok "backup directory exists"

$requiredFiles = @(
    "database.dump",
    "database.dump.sha256",
    "database.contents.txt",
    "origin-inventory.json",
    "backup-report.json",
    "pg-client-version.txt",
    "source-server-version.txt"
)

foreach ($fileName in $requiredFiles) {
    $filePath = Join-Path $backupPath $fileName
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
        Fail "required file missing: $fileName"
    }
}
Ok "required files are present"

$dumpPath = Join-Path $backupPath "database.dump"
$dumpInfo = Get-Item -LiteralPath $dumpPath
if ($dumpInfo.Length -le 0) {
    Fail "database.dump is empty"
}
Ok "database.dump is non-empty"

$shaFilePath = Join-Path $backupPath "database.dump.sha256"
$shaText = (Get-Content -LiteralPath $shaFilePath -Raw).Trim()
if ($shaText -notmatch "^[0-9a-fA-F]{64}(\s+\*?database\.dump)?$") {
    Fail "database.dump.sha256 is not a recognized SHA-256 manifest"
}

$expectedSha = ($shaText -split "\s+")[0].ToLowerInvariant()
$actualSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $dumpPath).Hash.ToLowerInvariant()
if ($actualSha -ne $expectedSha) {
    Fail "database.dump SHA-256 mismatch"
}
Ok "database.dump SHA-256 matches"

$jsonFiles = @("origin-inventory.json", "backup-report.json")
foreach ($fileName in $jsonFiles) {
    $filePath = Join-Path $backupPath $fileName
    try {
        Get-Content -LiteralPath $filePath -Raw | ConvertFrom-Json | Out-Null
    }
    catch {
        Fail "$fileName is not valid JSON"
    }
}
Ok "JSON files parse successfully"

$contentsPath = Join-Path $backupPath "database.contents.txt"
if ((Get-Item -LiteralPath $contentsPath).Length -le 0) {
    Fail "database.contents.txt is empty"
}
Ok "database.contents.txt is non-empty"

Write-Host "[oci-backup-artifact-check] backup artifact is ready for transfer validation"

