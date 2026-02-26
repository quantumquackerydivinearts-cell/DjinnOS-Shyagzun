param(
    [string]$Version = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Date -Format "yyyyMMdd-HHmmss")
}

$repoRoot = "C:\DjinnOS"
$releaseRoot = Join-Path $repoRoot "releases\$Version"
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

$desktopZip = Join-Path $repoRoot "apps\atelier-desktop\release\QuantumQuackeryAtelier-win32-x64.zip"
$apiZip = Join-Path $repoRoot "apps\atelier-api\release\atelier-api-bundle.zip"
$androidRoot = Join-Path $repoRoot "apps\atelier-desktop\release\android"

if (-not (Test-Path $desktopZip)) {
    throw "Desktop zip not found at $desktopZip"
}
if (-not (Test-Path $apiZip)) {
    throw "API zip not found at $apiZip"
}

$latestAndroid = Get-ChildItem -Directory $androidRoot -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestAndroid) {
    throw "No Android release directory found in $androidRoot"
}

Copy-Item -Force $desktopZip (Join-Path $releaseRoot "atelier-desktop-win32-x64.zip")
Copy-Item -Force $apiZip (Join-Path $releaseRoot "atelier-api-bundle.zip")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-release.apk") (Join-Path $releaseRoot "atelier-android-release.apk")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-release.aab") (Join-Path $releaseRoot "atelier-android-release.aab")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-debug.apk") (Join-Path $releaseRoot "atelier-android-debug.apk")

$manifest = [ordered]@{
    version = $Version
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    artifacts = @(
        "atelier-desktop-win32-x64.zip",
        "atelier-api-bundle.zip",
        "atelier-android-release.apk",
        "atelier-android-release.aab",
        "atelier-android-debug.apk"
    )
}

$manifestPath = Join-Path $releaseRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Out-File -FilePath $manifestPath -Encoding UTF8

$bundleZip = Join-Path (Split-Path $releaseRoot -Parent) ("atelier-suite-" + $Version + ".zip")
if (Test-Path $bundleZip) {
    Remove-Item -Force $bundleZip
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($releaseRoot, $bundleZip)

Get-ChildItem -File $releaseRoot | Select-Object Name,Length,LastWriteTime
Write-Host "Suite bundle created: $bundleZip"
