param(
    [Parameter(Mandatory = $true)]
    [string]$TenancyId,

    [string]$Region = "sa-saopaulo-1",
    [string]$VcnName = "sgi-vcn-public",
    [string]$InternetGatewayName = "sgi-prod-ig",
    [string]$NsgName = "sgi-prod-vm-nsg",
    [string]$OciExe = "oci",
    [switch]$Execute
)

$ErrorActionPreference = "Stop"
$Env:OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING = "True"

function Invoke-OciJson {
    param([string[]]$ArgsList)

    $output = & $OciExe @ArgsList
    if ($LASTEXITCODE -ne 0) {
        throw "OCI command failed: $OciExe $($ArgsList -join ' ')"
    }
    return ($output | Out-String | ConvertFrom-Json)
}

function Write-Step {
    param([string]$Message)
    Write-Host "[oci-network] $Message"
}

function ConvertTo-OciJson {
    param([object]$Value)

    return ($Value | ConvertTo-Json -Depth 20 -Compress)
}

$mode = if ($Execute) { "EXECUTE" } else { "DRY-RUN" }
Write-Step "mode=$mode region=$Region vcn=$VcnName"

$vcn = Invoke-OciJson @(
    "network", "vcn", "list",
    "--compartment-id", $TenancyId,
    "--region", $Region,
    "--display-name", $VcnName
)

if (-not $vcn.data -or $vcn.data.Count -eq 0) {
    throw "VCN '$VcnName' not found in compartment."
}

$vcnData = @($vcn.data)[0]
$vcnId = $vcnData.id
$routeTableId = $vcnData.'default-route-table-id'
Write-Step "found VCN state=$($vcnData.'lifecycle-state')"

if ($vcnData.'lifecycle-state' -ne "AVAILABLE") {
    throw "VCN is not AVAILABLE."
}

$igList = Invoke-OciJson @(
    "network", "internet-gateway", "list",
    "--compartment-id", $TenancyId,
    "--region", $Region,
    "--vcn-id", $vcnId
)

$ig = @($igList.data | Where-Object {
        $_.'display-name' -eq $InternetGatewayName -and $_.'lifecycle-state' -ne "TERMINATED"
    } | Select-Object -First 1)

if ($ig) {
    $igId = $ig.id
    Write-Step "internet gateway exists: $InternetGatewayName"
} elseif ($Execute) {
    Write-Step "creating internet gateway: $InternetGatewayName"
    $igCreated = Invoke-OciJson @(
        "network", "internet-gateway", "create",
        "--compartment-id", $TenancyId,
        "--region", $Region,
        "--vcn-id", $vcnId,
        "--display-name", $InternetGatewayName,
        "--is-enabled", "true",
        "--wait-for-state", "AVAILABLE"
    )
    $igId = $igCreated.data.id
} else {
    $igId = "<created-with--Execute>"
    Write-Step "would create internet gateway: $InternetGatewayName"
}

$routeTable = Invoke-OciJson @(
    "network", "route-table", "get",
    "--region", $Region,
    "--rt-id", $routeTableId
)

$routeRules = @($routeTable.data.'route-rules')
$defaultRoutes = @($routeRules | Where-Object { $_.'destination' -eq "0.0.0.0/0" })

if ($defaultRoutes.Count -gt 0) {
    $conflicting = @($defaultRoutes | Where-Object {
            $_.'network-entity-id' -ne $igId -and $_.'network-entity-id' -ne "<created-with--Execute>"
        })
    if ($conflicting.Count -gt 0) {
        throw "NO-GO: default route 0.0.0.0/0 already points to a different network entity."
    }
    Write-Step "default route already present"
} elseif ($Execute) {
    Write-Step "adding default route to internet gateway"
    $newRoute = [ordered]@{
        destination       = "0.0.0.0/0"
        destinationType   = "CIDR_BLOCK"
        networkEntityId   = $igId
        description       = "SGI OCI outbound Internet via Always Free VCN path"
    }
    $updatedRules = @($routeRules) + $newRoute
    $routeRulesJson = ConvertTo-OciJson $updatedRules
    Invoke-OciJson @(
        "network", "route-table", "update",
        "--region", $Region,
        "--rt-id", $routeTableId,
        "--route-rules", $routeRulesJson,
        "--force"
    ) | Out-Null
} else {
    Write-Step "would add default route 0.0.0.0/0 to internet gateway"
}

$nsgList = Invoke-OciJson @(
    "network", "nsg", "list",
    "--compartment-id", $TenancyId,
    "--region", $Region,
    "--vcn-id", $vcnId
)

$nsg = @($nsgList.data | Where-Object {
        $_.'display-name' -eq $NsgName -and $_.'lifecycle-state' -ne "TERMINATED"
    } | Select-Object -First 1)

if ($nsg) {
    $nsgId = $nsg.id
    Write-Step "NSG exists: $NsgName"
} elseif ($Execute) {
    Write-Step "creating NSG: $NsgName"
    $nsgCreated = Invoke-OciJson @(
        "network", "nsg", "create",
        "--compartment-id", $TenancyId,
        "--region", $Region,
        "--vcn-id", $vcnId,
        "--display-name", $NsgName,
        "--wait-for-state", "AVAILABLE"
    )
    $nsgId = $nsgCreated.data.id
} else {
    $nsgId = "<created-with--Execute>"
    Write-Step "would create NSG: $NsgName"
}

$plannedRules = @(
    [ordered]@{
        direction       = "EGRESS"
        protocol        = "6"
        destination     = "0.0.0.0/0"
        destinationType = "CIDR_BLOCK"
        tcpOptions      = @{ destinationPortRange = @{ min = 443; max = 443 } }
        description     = "HTTPS outbound for packages, registries, GitHub, Cloudflare Tunnel"
    },
    [ordered]@{
        direction       = "EGRESS"
        protocol        = "6"
        destination     = "0.0.0.0/0"
        destinationType = "CIDR_BLOCK"
        tcpOptions      = @{ destinationPortRange = @{ min = 80; max = 80 } }
        description     = "HTTP outbound for bootstrap redirects and repositories"
    },
    [ordered]@{
        direction       = "EGRESS"
        protocol        = "6"
        destination     = "0.0.0.0/0"
        destinationType = "CIDR_BLOCK"
        tcpOptions      = @{ destinationPortRange = @{ min = 53; max = 53 } }
        description     = "DNS TCP outbound"
    },
    [ordered]@{
        direction       = "EGRESS"
        protocol        = "17"
        destination     = "0.0.0.0/0"
        destinationType = "CIDR_BLOCK"
        udpOptions      = @{ destinationPortRange = @{ min = 53; max = 53 } }
        description     = "DNS UDP outbound"
    },
    [ordered]@{
        direction       = "EGRESS"
        protocol        = "17"
        destination     = "0.0.0.0/0"
        destinationType = "CIDR_BLOCK"
        udpOptions      = @{ destinationPortRange = @{ min = 7844; max = 7844 } }
        description     = "Cloudflare Tunnel QUIC outbound"
    }
)

if ($Execute) {
    $existingRules = Invoke-OciJson @(
        "network", "nsg", "rules", "list",
        "--region", $Region,
        "--nsg-id", $nsgId
    )

    $rulesToAdd = @()
    foreach ($rule in $plannedRules) {
        $exists = @($existingRules.data | Where-Object {
                $_.direction -eq $rule.direction -and $_.description -eq $rule.description
            }).Count -gt 0
        if (-not $exists) {
            $rulesToAdd += $rule
        }
    }

    if ($rulesToAdd.Count -gt 0) {
        Write-Step "adding NSG egress rules: $($rulesToAdd.Count)"
        $rulesJson = ConvertTo-OciJson $rulesToAdd
        Invoke-OciJson @(
            "network", "nsg", "rules", "add",
            "--region", $Region,
            "--nsg-id", $nsgId,
            "--security-rules", $rulesJson
        ) | Out-Null
    } else {
        Write-Step "NSG egress rules already present"
    }
} else {
    Write-Step "would add NSG egress rules: HTTPS, HTTP, DNS TCP, DNS UDP, Cloudflare QUIC"
}

Write-Step "done. No ingress rules are created by this script."
