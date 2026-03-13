Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [int]$Retries == 20,
    [int]$DelaySeconds = 1
)

function Test-Http200 {
    param([string]$Url)
    try {
        $resp = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 3 -UseBasicParsing
        return ($resp.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Wait-For {
    param(
        [string]$Name,
        [scriptblock]$Probe
    )
    for ($i = 1; $i -le $Retries; $i++) {
        if (& $Probe) {
            Write-Host "OK   $Name"
            return $true
        }
        Start-Sleep -Seconds $DelaySeconds
    }
    Write-Host "FAIL $Name"
    return $false
}

$kernelOk = Wait-For -Name "Kernel http://127.0.0.1:8000/events" -Probe { Test-Http200 -Url "http://127.0.0.1:8000/events" }
$apiOk = Wait-For -Name "Atelier API http://127.0.0.1:9000/health" -Probe { Test-Http200 -Url "http://127.0.0.1:9000/health" }
$desktopOk = Wait-For -Name "Desktop Dev tcp://127.0.0.1:5173" -Probe { Test-NetConnection -ComputerName 127.0.0.1 -Port 5173 -WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded }

if ($kernelOk -and $apiOk -and $desktopOk) {
    Write-Host "STACK READY"
    exit 0
}

Write-Host "STACK NOT READY"
exit 1
