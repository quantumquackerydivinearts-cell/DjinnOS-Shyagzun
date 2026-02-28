param(
    [ValidateSet("dev", "desktop")]
    [string]$UiMode = "dev",
    [string]$KernelHost = "127.0.0.1",
    [int]$KernelPort = 8000,
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 9000
)

$ErrorActionPreference = "Stop"

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSec = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

function New-EncodedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
}

function Start-ShellProcess {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$Workdir,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $script = "`$host.UI.RawUI.WindowTitle = '$Title'; Set-Location -LiteralPath '$Workdir'; $Command"
    $encoded = New-EncodedCommand -Command $script

    return Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-EncodedCommand", $encoded -PassThru
}

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$kernelRepo = Join-Path $repoRoot "DjinnOS-Shyagzun"
$apiRepo = Join-Path $repoRoot "apps/atelier-api"
$desktopRepo = Join-Path $repoRoot "apps/atelier-desktop"

if (-not (Test-Path -LiteralPath $kernelRepo)) {
    throw "Kernel repo not found: $kernelRepo"
}
if (-not (Test-Path -LiteralPath $apiRepo)) {
    throw "API repo not found: $apiRepo"
}
if (-not (Test-Path -LiteralPath $desktopRepo)) {
    throw "Desktop repo not found: $desktopRepo"
}

$npmCmd = "C:\Program Files\nodejs\npm.cmd"
if (-not (Test-Path -LiteralPath $npmCmd)) {
    throw "npm not found at $npmCmd"
}

Write-Host "Starting kernel service on ${KernelHost}:${KernelPort}"
$kernelCmd = "py -m uvicorn shygazun.kernel_service:app --host $KernelHost --port $KernelPort --app-dir '$kernelRepo'"
$kernelProc = Start-ShellProcess -Title "Atelier Kernel" -Workdir $kernelRepo -Command $kernelCmd

if (-not (Test-HttpReady -Url "http://${KernelHost}:${KernelPort}/events" -TimeoutSec 90)) {
    throw "Kernel did not become ready on http://${KernelHost}:${KernelPort}"
}

Write-Host "Starting API service on ${ApiHost}:${ApiPort}"
$sqlitePath = (Join-Path $apiRepo "atelier_local.db") -replace "\\", "/"
$apiCmd = "`$env:DATABASE_URL='sqlite:///$sqlitePath'; `$env:KERNEL_BASE_URL='http://${KernelHost}:${KernelPort}'; `$env:PYTHONPATH='$repoRoot;$apiRepo'; py -m uvicorn atelier_api.main:app --host $ApiHost --port $ApiPort --app-dir '$apiRepo'"
$apiProc = Start-ShellProcess -Title "Atelier API" -Workdir $apiRepo -Command $apiCmd

if (-not (Test-HttpReady -Url "http://${ApiHost}:${ApiPort}/health" -TimeoutSec 90)) {
    throw "API did not become ready on http://${ApiHost}:${ApiPort}"
}

if ($UiMode -eq "dev") {
    Write-Host "Starting desktop dev shell"
    $uiCmd = "& '$npmCmd' run dev"
    $null = Start-ShellProcess -Title "Atelier Desktop" -Workdir $desktopRepo -Command $uiCmd
} else {
    $exe = Join-Path $desktopRepo "release/QuantumQuackeryAtelier-win32-x64/QuantumQuackeryAtelier.exe"
    if (-not (Test-Path -LiteralPath $exe)) {
        throw "Desktop executable not found: $exe"
    }
    Write-Host "Starting packaged desktop"
    Start-Process -FilePath $exe | Out-Null
}

Write-Host "Boot complete."
Write-Host "Kernel PID: $($kernelProc.Id)"
Write-Host "API PID: $($apiProc.Id)"
Write-Host "Kernel URL: http://${KernelHost}:${KernelPort}"
Write-Host "API URL: http://${ApiHost}:${ApiPort}"
