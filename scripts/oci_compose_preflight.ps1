param(
    [string]$ComposeProjectName = "sig-v2-oci-preflight"
)

$ErrorActionPreference = "Stop"

function Fail {
    param([string]$Message)
    Write-Error "[oci-compose-preflight] $Message"
    exit 1
}

function Ok {
    param([string]$Message)
    Write-Host "[oci-compose-preflight] OK: $Message"
}

$env:CLOUDFLARE_TUNNEL_TOKEN = "dummy-preflight-token"
if (-not $env:BACKEND_WORKERS) {
    $env:BACKEND_WORKERS = "1"
}

$composeArgs = @(
    "-p", $ComposeProjectName,
    "-f", "docker-compose.yml",
    "-f", "docker-compose.prod.yml",
    "-f", "docker-compose.oci.yml",
    "config"
)

$rendered = & docker compose @composeArgs 2>$null
if ($LASTEXITCODE -ne 0) {
    Fail "docker compose config failed"
}

$text = ($rendered -join "`n")

if ($text -match "(?ms)^  backend:.*?^    ports:") {
    Fail "backend publishes host ports"
}
Ok "backend does not publish host ports"

if ($text -match "(?ms)^  frontend:.*?^    ports:") {
    Fail "frontend publishes host ports"
}
Ok "frontend does not publish host ports"

if ($text -notmatch "(?m)^  cloudflared:") {
    Fail "cloudflared service is missing"
}
Ok "cloudflared service is present"

if ($text -notmatch "(?ms)^  backend:.*?--workers\s*\n\s*-\s*""1""") {
    Fail "backend worker count is not rendered as 1"
}
Ok "backend worker count renders as 1"

if ($text -match "CLOUDFLARE_TUNNEL_TOKEN=.*[A-Za-z0-9_-]{20}") {
    Fail "rendered config appears to include a real tunnel token"
}
Ok "no real tunnel token pattern found"

Write-Host "[oci-compose-preflight] preflight passed"
