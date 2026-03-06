param(
    [string]$OutPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path (Split-Path $bootstrapRoot -Parent) -Parent
if ([string]::IsNullOrWhiteSpace($OutPath)) {
    $OutPath = Join-Path $repoRoot "releases\atelier-bootstrap-installer.zip"
}

$outDir = Split-Path -Parent $OutPath
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

if (Test-Path -LiteralPath $OutPath) {
    Remove-Item -Force -LiteralPath $OutPath
}

$launcherBuilder = Join-Path $bootstrapRoot "build_launcher_exe.ps1"
$launcherExe = Join-Path $bootstrapRoot "Launch-Atelier.exe"
$iconPath = Join-Path $repoRoot "apps\atelier-desktop\public\icon.ico"
if (Test-Path -LiteralPath $launcherBuilder) {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $launcherBuilder -OutExePath $launcherExe -IconPath $iconPath
    } catch {
        Write-Warning ("launch_exe_build_failed: " + $_.Exception.Message)
    }
}

$include = @(
    "Install-Atelier.ps1",
    "Launch-Atelier.ps1",
    "Setup-Wizard.ps1",
    "Setup-Wizard.cmd",
    "config.template.json",
    "README-quickstart.txt",
    "build_launcher_exe.ps1"
)

if (Test-Path -LiteralPath $launcherExe) {
    $include += "Launch-Atelier.exe"
}

$paths = $include | ForEach-Object { Join-Path $bootstrapRoot $_ }
$paths += $iconPath
Compress-Archive -Path $paths -DestinationPath $OutPath -CompressionLevel Optimal

Get-Item -LiteralPath $OutPath | Select-Object FullName,Length,LastWriteTime
