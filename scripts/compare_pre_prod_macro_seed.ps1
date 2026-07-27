[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$FirstEvidence,

    [Parameter(Mandatory = $true)]
    [string]$SecondEvidence,

    [Parameter(Mandatory = $true)]
    [string]$RunId
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($RunId -notmatch '^\d{8}-\d{6}$') {
    throw "RunId deve seguir o formato YYYYMMDD-HHMMSS."
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ArtifactDirectory = Join-Path $RepoRoot "artifacts/pre-prod-rebuild/$RunId"
$OutputPath = Join-Path $ArtifactDirectory "macro-seed-compare.json"

if (Test-Path -LiteralPath $OutputPath) {
    throw "A evidência de comparação já existe: $OutputPath"
}

$FirstPath = (Resolve-Path -LiteralPath $FirstEvidence).Path
$SecondPath = (Resolve-Path -LiteralPath $SecondEvidence).Path

New-Item -ItemType Directory -Path $ArtifactDirectory -Force | Out-Null

$PreviousLocation = Get-Location
try {
    Set-Location (Join-Path $RepoRoot "backend")

    $PythonScript = @'
import json
import sys
from pathlib import Path

from app.services.pre_prod_macro_seed_compare import compare_macro_seed_files

first_path = Path(sys.argv[1])
second_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])

result = compare_macro_seed_files(first_path, second_path)
payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
output_path.write_text(payload, encoding="utf-8")
print(payload, end="")
raise SystemExit(0 if result.ok else 1)
'@

    $PythonScript | python - $FirstPath $SecondPath $OutputPath
    $ExitCode = $LASTEXITCODE

    if (-not (Test-Path -LiteralPath $OutputPath)) {
        throw "O comparador não gerou a evidência esperada: $OutputPath"
    }

    $Payload = Get-Content -LiteralPath $OutputPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Payload.schema_version -ne "pre-prod-macro-seed-compare.v1") {
        throw "schema_version inesperado na evidência de comparação."
    }
    if ($Payload.ok -ne $true -or $ExitCode -ne 0) {
        throw "A comparação macroeconômica falhou. Consulte $OutputPath"
    }

    [ordered]@{
        run_id = $RunId
        evidence_path = $OutputPath
        schema_version = $Payload.schema_version
        first_run_id = $Payload.first_run_id
        second_run_id = $Payload.second_run_id
        ok = $Payload.ok
    } | ConvertTo-Json
}
finally {
    Set-Location $PreviousLocation
}
