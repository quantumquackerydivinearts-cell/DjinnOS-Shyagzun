param(
    [string]$DownloadUrl = "",
    [string]$SuiteZipPath = "",
    [string]$InstallRoot = "$env:LOCALAPPDATA\KosLabyrnth\Atelier-Hosted",
    [string]$ApiBaseUrl = "http://127.0.0.1:9000",
    [string]$KernelBaseUrl = "http://127.0.0.1:8000",
    [switch]$Force,
    [switch]$RunAfterInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Path {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required path not found: $Path"
    }
}

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Stop-AtelierProcesses {
    param([Parameter(Mandatory = $true)][string]$InstallRoot)

    $normalizedRoot = [System.IO.Path]::GetFullPath($InstallRoot).TrimEnd("\")
    $currentPid = $PID
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction Stop
    } catch {
        $procs = @()
    }

    foreach ($proc in $procs) {
        $procId = 0
        if (-not [int]::TryParse([string]$proc.ProcessId, [ref]$procId)) { continue }
        if ($procId -eq $currentPid -or $procId -le 0) { continue }
        $commandLine = ""
        $executablePath = ""
        try { $commandLine = [string]$proc.CommandLine } catch { }
        try { $executablePath = [string]$proc.ExecutablePath } catch { }
        $matchesInstallRoot = $false
        if (-not [string]::IsNullOrWhiteSpace($commandLine) -and $commandLine.IndexOf($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $matchesInstallRoot = $true
        }
        if (-not $matchesInstallRoot -and -not [string]::IsNullOrWhiteSpace($executablePath)) {
            try {
                $normalizedExe = [System.IO.Path]::GetFullPath($executablePath)
                if ($normalizedExe.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                    $matchesInstallRoot = $true
                }
            } catch {
            }
        }
        if ($matchesInstallRoot) {
            try { Stop-Process -Id $procId -Force -ErrorAction Stop } catch { }
        }
    }

    Start-Sleep -Milliseconds 750
}

function Remove-DirectoryRobust {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return }
    for ($attempt = 1; $attempt -le 5; $attempt++) {
        try {
            Remove-Item -Recurse -Force -LiteralPath $Path -ErrorAction Stop
            return
        } catch {
            if ($attempt -eq 5) { throw }
            Start-Sleep -Milliseconds (500 * $attempt)
        }
    }
}

function Unblock-Tree {
    param([Parameter(Mandatory = $true)][string]$Root)
    if (-not (Test-Path -LiteralPath $Root)) { return }
    Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            try { Unblock-File -LiteralPath $_.FullName -ErrorAction Stop } catch { }
        }
}

function Write-Shortcut {
    param(
        [Parameter(Mandatory = $true)][string]$ShortcutPath,
        [Parameter(Mandatory = $true)][string]$TargetPath,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Arguments,
        [string]$WorkingDirectory = "",
        [string]$IconLocation = ""
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    if ($null -ne $Arguments) { $shortcut.Arguments = $Arguments }
    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) { $shortcut.WorkingDirectory = $WorkingDirectory }
    if (-not [string]::IsNullOrWhiteSpace($IconLocation)) { $shortcut.IconLocation = $IconLocation }
    $shortcut.Save()
}

function Read-SuiteManifest {
    param([Parameter(Mandatory = $true)][string]$ManifestPath)
    try {
        return Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

if ([string]::IsNullOrWhiteSpace($SuiteZipPath) -and [string]::IsNullOrWhiteSpace($DownloadUrl)) {
    throw "Provide either -SuiteZipPath <local-zip> or -DownloadUrl <public-url>."
}
if ([string]::IsNullOrWhiteSpace($ApiBaseUrl)) { throw "ApiBaseUrl is required." }
if ([string]::IsNullOrWhiteSpace($KernelBaseUrl)) { throw "KernelBaseUrl is required." }

$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchTemplatePath = Join-Path $bootstrapRoot "Launch-Atelier.ps1"
$launchExeTemplatePath = Join-Path $bootstrapRoot "Launch-Atelier.exe"
$configTemplatePath = Join-Path $bootstrapRoot "config.hosted.template.json"

Require-Path -Path $launchTemplatePath
Require-Path -Path $configTemplatePath

$tempRoot = Join-Path $env:TEMP ("atelier-hosted-bootstrap-" + [guid]::NewGuid().ToString("N"))
Ensure-Directory -Path $tempRoot

try {
    if (-not [string]::IsNullOrWhiteSpace($SuiteZipPath)) {
        $suiteZipResolved = [System.IO.Path]::GetFullPath($SuiteZipPath)
        Require-Path -Path $suiteZipResolved
    } else {
        $suiteZipResolved = Join-Path $tempRoot "atelier-hosted-suite.zip"
        Write-Host "Downloading hosted suite archive..."
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $suiteZipResolved -UseBasicParsing
    }

    if (Test-Path -LiteralPath $InstallRoot) {
        Write-Host "Existing hosted install detected. Stopping running Atelier processes..."
        Stop-AtelierProcesses -InstallRoot $InstallRoot
        Write-Host "Removing existing hosted install..."
        Remove-DirectoryRobust -Path $InstallRoot
    }

    Ensure-Directory -Path $InstallRoot

    $expandedSuite = Join-Path $tempRoot "suite"
    Ensure-Directory -Path $expandedSuite
    Expand-Archive -Path $suiteZipResolved -DestinationPath $expandedSuite -Force

    $suiteManifest = Join-Path $expandedSuite "manifest.json"
    $desktopZip = Join-Path $expandedSuite "atelier-desktop-win32-x64.zip"
    $apiZip = Join-Path $expandedSuite "atelier-api-bundle.zip"
    $hostedDeploymentDir = Join-Path $expandedSuite "hosted-deployment"
    $androidReleaseApk = Join-Path $expandedSuite "atelier-android-release.apk"
    $androidReleaseAab = Join-Path $expandedSuite "atelier-android-release.aab"
    $androidDebugApk = Join-Path $expandedSuite "atelier-android-debug.apk"

    Require-Path -Path $suiteManifest
    $manifest = Read-SuiteManifest -ManifestPath $suiteManifest
    if ($null -eq $manifest -or $manifest.target -ne "hosted") {
        throw "This installer only supports the Hosted Atelier Stack."
    }

    Require-Path -Path $desktopZip
    Require-Path -Path $apiZip
    Require-Path -Path $hostedDeploymentDir

    $desktopDir = Join-Path $InstallRoot "desktop"
    $apiDir = Join-Path $InstallRoot "api"
    $hostedDir = Join-Path $InstallRoot "hosted-deployment"
    $androidDir = Join-Path $InstallRoot "android"
    $metaDir = Join-Path $InstallRoot "meta"

    Ensure-Directory -Path $desktopDir
    Ensure-Directory -Path $apiDir
    Ensure-Directory -Path $hostedDir
    Ensure-Directory -Path $androidDir
    Ensure-Directory -Path $metaDir

    Expand-Archive -Path $desktopZip -DestinationPath $desktopDir -Force
    Expand-Archive -Path $apiZip -DestinationPath $apiDir -Force
    Copy-Item -Recurse -Force $hostedDeploymentDir\* $hostedDir
    Unblock-Tree -Root $desktopDir
    Unblock-Tree -Root $apiDir
    Unblock-Tree -Root $hostedDir

    if (Test-Path -LiteralPath $androidReleaseApk) { Copy-Item -Force $androidReleaseApk (Join-Path $androidDir "atelier-android-release.apk") }
    if (Test-Path -LiteralPath $androidReleaseAab) { Copy-Item -Force $androidReleaseAab (Join-Path $androidDir "atelier-android-release.aab") }
    if (Test-Path -LiteralPath $androidDebugApk) { Copy-Item -Force $androidDebugApk (Join-Path $androidDir "atelier-android-debug.apk") }

    Copy-Item -Force $suiteManifest (Join-Path $metaDir "suite-manifest.json")

    $launchInstalledPath = Join-Path $InstallRoot "Launch-Atelier.ps1"
    $launchExeInstalledPath = Join-Path $InstallRoot "Launch-Atelier.exe"
    $launchVbsInstalledPath = Join-Path $InstallRoot "Launch-Atelier.vbs"
    Copy-Item -Force $launchTemplatePath $launchInstalledPath
    if (Test-Path -LiteralPath $launchExeTemplatePath) {
        Copy-Item -Force $launchExeTemplatePath $launchExeInstalledPath
    }

    $configRaw = Get-Content -LiteralPath $configTemplatePath -Raw
    $configRaw = $configRaw.Replace("__API_BASE_URL__", $ApiBaseUrl)
    $configRaw = $configRaw.Replace("__KERNEL_BASE_URL__", $KernelBaseUrl)
    $configRaw | Set-Content -LiteralPath (Join-Path $InstallRoot "config.json") -Encoding ASCII

    @"
Set shell = CreateObject("WScript.Shell")
cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File ""$launchInstalledPath"""
shell.Run cmd, 0
"@ | Set-Content -LiteralPath $launchVbsInstalledPath -Encoding ASCII

    $desktopIconCandidate = Get-ChildItem -Path $desktopDir -Recurse -File -Filter "icon.ico" -ErrorAction SilentlyContinue | Select-Object -First 1
    $desktopIconPath = if ($desktopIconCandidate) { $desktopIconCandidate.FullName } else { "" }
    $shortcutIconLocation = ""
    if ((-not [string]::IsNullOrWhiteSpace($desktopIconPath)) -and (Test-Path -LiteralPath $desktopIconPath)) {
        $shortcutIconLocation = $desktopIconPath + ",0"
    } elseif (Test-Path -LiteralPath $launchExeInstalledPath) {
        $shortcutIconLocation = $launchExeInstalledPath + ",0"
    }

    $desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ko's Labyrnth Atelier Hosted.lnk"
    $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Ko's Labyrnth"
    Ensure-Directory -Path $startMenuDir
    $startMenuShortcut = Join-Path $startMenuDir "Ko's Labyrnth Atelier Hosted.lnk"

    $wscriptExe = Join-Path $env:WINDIR "System32\wscript.exe"
    $wscriptArgs = "`"$launchVbsInstalledPath`""
    Write-Shortcut -ShortcutPath $desktopShortcut -TargetPath $wscriptExe -Arguments $wscriptArgs -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation
    Write-Shortcut -ShortcutPath $startMenuShortcut -TargetPath $wscriptExe -Arguments $wscriptArgs -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation

    Write-Host "Hosted install complete."
    Write-Host "Install root: $InstallRoot"
    Write-Host "Desktop shortcut: $desktopShortcut"
    Write-Host "Start menu shortcut: $startMenuShortcut"
    Write-Host "Hosted deployment files: $hostedDir"

    if ($RunAfterInstall) {
        Start-Process -FilePath $wscriptExe -ArgumentList $wscriptArgs | Out-Null
    }
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -Recurse -Force -LiteralPath $tempRoot
    }
}
