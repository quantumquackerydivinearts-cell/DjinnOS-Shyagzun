param(
    [string]$Version = "",
    [switch]$SkipNpmInstall,
    [switch]$SkipDebug,
    [switch]$DebugOnly,
    [string]$ApiBaseUrl = "",
    [string]$KeystorePath = "",
    [string]$StorePassword = "",
    [string]$KeyAlias = "",
    [string]$KeyPassword = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Date -Format "yyyyMMdd-HHmmss")
}

$repoRoot = "C:\DjinnOS"
$desktopRoot = Join-Path $repoRoot "apps\atelier-desktop"
$androidRoot = Join-Path $desktopRoot "android"
$appRoot = Join-Path $androidRoot "app"

$node = "C:\Program Files\nodejs\npm.cmd"
if (-not (Test-Path $node)) {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "npm.cmd not found"
    }
    $node = $cmd.Source
}

$jdk = "C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot"
if (-not (Test-Path $jdk)) {
    throw "JDK not found at $jdk"
}

$sdk = "C:\Users\quant\AppData\Local\Android\Sdk"
if (-not (Test-Path $sdk)) {
    throw "Android SDK not found at $sdk"
}

$env:JAVA_HOME = $jdk
$env:ANDROID_HOME = $sdk
$env:Path = "$jdk\bin;$sdk\platform-tools;$sdk\cmdline-tools\latest\bin;$env:Path"

"sdk.dir=$($sdk -replace '\\','\\')" | Out-File -FilePath (Join-Path $androidRoot "local.properties") -Encoding ascii -Force

Push-Location $desktopRoot
try {
    if (-not $SkipNpmInstall) {
        & $node install
    }
    if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
        & $node run mobile:sync
    } else {
        $env:VITE_API_BASE = $ApiBaseUrl
        & $node run mobile:sync
    }
} finally {
    Pop-Location
}

if ($DebugOnly) {
    $SkipDebug = $false
}

if (-not $DebugOnly) {
    $resolvedKeystorePath = if ([string]::IsNullOrWhiteSpace($KeystorePath)) { [Environment]::GetEnvironmentVariable("ATELIER_ANDROID_KEYSTORE") } else { $KeystorePath }
    $resolvedStorePassword = if ([string]::IsNullOrWhiteSpace($StorePassword)) { [Environment]::GetEnvironmentVariable("ATELIER_ANDROID_KEYSTORE_PASSWORD") } else { $StorePassword }
    $resolvedKeyAlias = if ([string]::IsNullOrWhiteSpace($KeyAlias)) { [Environment]::GetEnvironmentVariable("ATELIER_ANDROID_KEY_ALIAS") } else { $KeyAlias }
    $resolvedKeyPassword = if ([string]::IsNullOrWhiteSpace($KeyPassword)) { [Environment]::GetEnvironmentVariable("ATELIER_ANDROID_KEY_PASSWORD") } else { $KeyPassword }

    $missing = @()
    if ([string]::IsNullOrWhiteSpace($resolvedKeystorePath)) { $missing += "ATELIER_ANDROID_KEYSTORE or -KeystorePath" }
    if ([string]::IsNullOrWhiteSpace($resolvedStorePassword)) { $missing += "ATELIER_ANDROID_KEYSTORE_PASSWORD or -StorePassword" }
    if ([string]::IsNullOrWhiteSpace($resolvedKeyAlias)) { $missing += "ATELIER_ANDROID_KEY_ALIAS or -KeyAlias" }
    if ([string]::IsNullOrWhiteSpace($resolvedKeyPassword)) { $missing += "ATELIER_ANDROID_KEY_PASSWORD or -KeyPassword" }

    if ($missing.Count -gt 0) {
        $joined = [string]::Join(", ", $missing)
        throw "Release signing requires: $joined. Use -DebugOnly for local debug build without release artifacts."
    }

    if (-not (Test-Path $resolvedKeystorePath)) {
        throw "ATELIER_ANDROID_KEYSTORE path not found: $resolvedKeystorePath"
    }

    # Make variables available to Gradle in this process.
    $env:ATELIER_ANDROID_KEYSTORE = $resolvedKeystorePath
    $env:ATELIER_ANDROID_KEYSTORE_PASSWORD = $resolvedStorePassword
    $env:ATELIER_ANDROID_KEY_ALIAS = $resolvedKeyAlias
    $env:ATELIER_ANDROID_KEY_PASSWORD = $resolvedKeyPassword
}

Push-Location $androidRoot
try {
    if ($DebugOnly) {
        & .\gradlew.bat assembleDebug --no-daemon
    } elseif ($SkipDebug) {
        & .\gradlew.bat assembleRelease bundleRelease --no-daemon
    } else {
        & .\gradlew.bat assembleDebug assembleRelease bundleRelease --no-daemon
    }
} finally {
    Pop-Location
}

$outRoot = Join-Path $desktopRoot "release\android\$Version"
New-Item -ItemType Directory -Force -Path $outRoot | Out-Null

$apkDebug = Join-Path $appRoot "build\outputs\apk\debug\app-debug.apk"
$apkRelease = Join-Path $appRoot "build\outputs\apk\release\app-release.apk"
$aabRelease = Join-Path $appRoot "build\outputs\bundle\release\app-release.aab"

if (Test-Path $apkDebug) { Copy-Item -Force $apkDebug (Join-Path $outRoot "app-debug.apk") }
if ((-not $DebugOnly) -and (Test-Path $apkRelease)) { Copy-Item -Force $apkRelease (Join-Path $outRoot "app-release.apk") }
if ((-not $DebugOnly) -and (Test-Path $aabRelease)) { Copy-Item -Force $aabRelease (Join-Path $outRoot "app-release.aab") }

Get-ChildItem -File $outRoot | Select-Object FullName,Length,LastWriteTime
Write-Host "Android artifacts prepared in: $outRoot"
