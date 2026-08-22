param(
    [int]$PostgresPasswordLength = 32,
    [int]$SecretKeyBytes = 32,
    [int]$AdminPasswordLength = 32
)

$ErrorActionPreference = "Stop"

function New-UrlSafeSecret {
    param([int]$Length)

    $alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-"
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }

    $chars = for ($i = 0; $i -lt $Length; $i++) {
        $alphabet[$bytes[$i] % $alphabet.Length]
    }
    -join $chars
}

function New-HexSecret {
    param([int]$Bytes)

    $bytesValue = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytesValue)
    }
    finally {
        $rng.Dispose()
    }
    ($bytesValue | ForEach-Object { $_.ToString("x2") }) -join ""
}

Write-Host "[oci-generate-env-secrets] Generated values. Paste only into the VM-local .env."
Write-Host "[oci-generate-env-secrets] Do not commit, screenshot, or paste these values into tickets/docs."
Write-Host ""
Write-Host "POSTGRES_PASSWORD=$(New-UrlSafeSecret -Length $PostgresPasswordLength)"
Write-Host "SECRET_KEY=$(New-HexSecret -Bytes $SecretKeyBytes)"
Write-Host "SUPERADMIN_PASSWORD=$(New-UrlSafeSecret -Length $AdminPasswordLength)"
