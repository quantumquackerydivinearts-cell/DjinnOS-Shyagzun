param(
    [string]$OutExePath = "",
    [string]$IconPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Path {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required path not found: $Path"
    }
}

$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path (Split-Path $bootstrapRoot -Parent) -Parent
$launcherPs1 = Join-Path $bootstrapRoot "Launch-Atelier.ps1"

if ([string]::IsNullOrWhiteSpace($OutExePath)) {
    $OutExePath = Join-Path $bootstrapRoot "Launch-Atelier.exe"
}
if ([string]::IsNullOrWhiteSpace($IconPath)) {
    $IconPath = Join-Path $repoRoot "apps\atelier-desktop\public\icon.ico"
}

Require-Path -Path $launcherPs1
Require-Path -Path $IconPath

if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    throw "ps2exe module is required. Install once with: Install-Module ps2exe -Scope CurrentUser"
}

Import-Module ps2exe -ErrorAction Stop

if (Test-Path -LiteralPath $OutExePath) {
    Remove-Item -Force -LiteralPath $OutExePath
}

Invoke-ps2exe `
    -inputFile $launcherPs1 `
    -outputFile $OutExePath `
    -iconFile $IconPath `
    -title "Ko's Labyrnth Atelier Launcher" `
    -description "Local launcher for Ko's Labyrnth Atelier" `
    -product "Ko's Labyrnth Atelier" `
    -company "Ko's Labyrnth" `
    -copyright "Ko's Labyrnth" `
    -version "0.1.1.0" `
    -noConsole

if (-not (Test-Path -LiteralPath $OutExePath)) {
    throw "Launcher EXE was not generated: $OutExePath"
}

Get-Item -LiteralPath $OutExePath | Select-Object FullName,Length,LastWriteTime
