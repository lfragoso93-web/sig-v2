[CmdletBinding()]
param(
    [string]$RunId = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [string]$Branch = "stable-15jun",
    [string]$CommitSha,
    [string]$ComposeService = "backend"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Comando obrigatório não encontrado: $Name"
    }
}

Assert-CommandAvailable -Name "git"
Assert-CommandAvailable -Name "docker"

if ($RunId -notmatch '^\d{8}-\d{6}$') {
    throw "RunId deve seguir o formato YYYYMMDD-HHMMSS."
}

$RepositoryRoot = (git rev-parse --show-toplevel).Trim()
if (-not $RepositoryRoot) {
    throw "Não foi possível localizar a raiz do repositório Git."
}

Push-Location $RepositoryRoot
try {
    $CurrentBranch = (git branch --show-current).Trim()
    if ($CurrentBranch -ne $Branch) {
        throw "Branch atual '$CurrentBranch' difere da branch operacional obrigatória '$Branch'."
    }

    if (-not $CommitSha) {
        $CommitSha = (git rev-parse HEAD).Trim()
    }

    if ($CommitSha -notmatch '^[0-9a-f]{40}$') {
        throw "CommitSha deve conter 40 caracteres hexadecimais minúsculos."
    }

    $HeadSha = (git rev-parse HEAD).Trim()
    if ($HeadSha -ne $CommitSha) {
        throw "CommitSha informado não corresponde ao HEAD atual."
    }

    $ArtifactDirectory = Join-Path $RepositoryRoot "artifacts/pre-prod-rebuild/$RunId"
    New-Item -ItemType Directory -Path $ArtifactDirectory -Force | Out-Null

    $EvidencePath = Join-Path $ArtifactDirectory "macro-seed.json"
    $TemporaryPath = Join-Path $ArtifactDirectory "macro-seed.tmp"

    if (Test-Path $EvidencePath) {
        throw "A evidência já existe: $EvidencePath"
    }

    $Output = & docker compose exec -T `
        -e "PRE_PROD_BRANCH=$Branch" `
        -e "PRE_PROD_COMMIT_SHA=$CommitSha" `
        $ComposeService python -m app.cli.pre_prod_macro_seed `
        --run-id $RunId `
        --branch $Branch `
        --commit-sha $CommitSha 2>&1

    $ExitCode = $LASTEXITCODE
    $OutputText = ($Output | Out-String).Trim()

    Set-Content -Path $TemporaryPath -Value $OutputText -Encoding utf8
    Move-Item -Path $TemporaryPath -Destination $EvidencePath -Force

    if ($ExitCode -ne 0) {
        throw "Seed macro falhou com código $ExitCode. Evidência preservada em $EvidencePath"
    }

    try {
        $Evidence = Get-Content $EvidencePath -Raw | ConvertFrom-Json
    }
    catch {
        throw "A saída não contém JSON válido. Evidência preservada em $EvidencePath"
    }

    if (-not $Evidence.ok) {
        throw "A evidência reportou ok=false. Arquivo: $EvidencePath"
    }

    [ordered]@{
        run_id = $RunId
        branch = $Branch
        commit_sha = $CommitSha
        evidence_path = $EvidencePath
        schema_version = $Evidence.schema_version
        ok = $Evidence.ok
    } | ConvertTo-Json -Depth 4
}
finally {
    if (Test-Path $TemporaryPath -ErrorAction SilentlyContinue) {
        Remove-Item $TemporaryPath -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}
