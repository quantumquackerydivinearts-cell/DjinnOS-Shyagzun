param(
    [string]$DownloadUrl = "",
    [string]$SuiteZipPath = "",
    [string]$InstallRoot = "$env:LOCALAPPDATA\KosLabyrnth\Atelier",
    [switch]$Force,
    [switch]$RunAfterInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Path {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required path not found: $Path"
    }
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Write-Shortcut {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ShortcutPath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Arguments,
        [string]$WorkingDirectory = "",
        [string]$IconLocation = ""
    )

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($ShortcutPath)
    $shortcut.TargetPath = $TargetPath
    if ($null -ne $Arguments) {
        $shortcut.Arguments = $Arguments
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        $shortcut.WorkingDirectory = $WorkingDirectory
    }
    if (-not [string]::IsNullOrWhiteSpace($IconLocation)) {
        $shortcut.IconLocation = $IconLocation
    }
    $shortcut.Save()
}

if ([string]::IsNullOrWhiteSpace($SuiteZipPath) -and [string]::IsNullOrWhiteSpace($DownloadUrl)) {
    throw "Provide either -SuiteZipPath <local-zip> or -DownloadUrl <public-url>."
}

$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launchTemplatePath = Join-Path $bootstrapRoot "Launch-Atelier.ps1"
$launchExeTemplatePath = Join-Path $bootstrapRoot "Launch-Atelier.exe"
$configTemplatePath = Join-Path $bootstrapRoot "config.template.json"

Require-Path -Path $launchTemplatePath
Require-Path -Path $configTemplatePath

$tempRoot = Join-Path $env:TEMP ("atelier-bootstrap-" + [guid]::NewGuid().ToString("N"))
Ensure-Directory -Path $tempRoot

$suiteZipResolved = ""
try {
    if (-not [string]::IsNullOrWhiteSpace($SuiteZipPath)) {
        $suiteZipResolved = [System.IO.Path]::GetFullPath($SuiteZipPath)
        Require-Path -Path $suiteZipResolved
    } else {
        $suiteZipResolved = Join-Path $tempRoot "atelier-suite.zip"
        Write-Host "Downloading suite archive..."
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $suiteZipResolved -UseBasicParsing
    }

    if ((Test-Path -LiteralPath $InstallRoot) -and -not $Force) {
        throw "Install root already exists: $InstallRoot (rerun with -Force to overwrite)"
    }

    if (Test-Path -LiteralPath $InstallRoot) {
        Remove-Item -Recurse -Force -LiteralPath $InstallRoot
    }

    Ensure-Directory -Path $InstallRoot

    $expandedSuite = Join-Path $tempRoot "suite"
    Ensure-Directory -Path $expandedSuite
    Expand-Archive -Path $suiteZipResolved -DestinationPath $expandedSuite -Force

    $desktopZip = Join-Path $expandedSuite "atelier-desktop-win32-x64.zip"
    $apiZip = Join-Path $expandedSuite "atelier-api-bundle.zip"
    $kernelZip = Join-Path $expandedSuite "kernel-runtime-bundle.zip"
    $wheelhouseZip = Join-Path $expandedSuite "python-wheelhouse.zip"
    $androidReleaseApk = Join-Path $expandedSuite "atelier-android-release.apk"
    $androidReleaseAab = Join-Path $expandedSuite "atelier-android-release.aab"
    $androidDebugApk = Join-Path $expandedSuite "atelier-android-debug.apk"
    $suiteManifest = Join-Path $expandedSuite "manifest.json"

    Require-Path -Path $desktopZip
    Require-Path -Path $apiZip
    Require-Path -Path $kernelZip
    Require-Path -Path $wheelhouseZip
    Require-Path -Path $suiteManifest

    $desktopDir = Join-Path $InstallRoot "desktop"
    $apiDir = Join-Path $InstallRoot "api"
    $kernelDir = Join-Path $InstallRoot "kernel"
    $wheelhouseDir = Join-Path $InstallRoot "wheelhouse"
    $androidDir = Join-Path $InstallRoot "android"
    $metaDir = Join-Path $InstallRoot "meta"

    Ensure-Directory -Path $desktopDir
    Ensure-Directory -Path $apiDir
    Ensure-Directory -Path $kernelDir
    Ensure-Directory -Path $wheelhouseDir
    Ensure-Directory -Path $androidDir
    Ensure-Directory -Path $metaDir

    Expand-Archive -Path $desktopZip -DestinationPath $desktopDir -Force
    Expand-Archive -Path $apiZip -DestinationPath $apiDir -Force
    Expand-Archive -Path $kernelZip -DestinationPath $kernelDir -Force
    Expand-Archive -Path $wheelhouseZip -DestinationPath $wheelhouseDir -Force

    if (Test-Path -LiteralPath $androidReleaseApk) { Copy-Item -Force $androidReleaseApk (Join-Path $androidDir "atelier-android-release.apk") }
    if (Test-Path -LiteralPath $androidReleaseAab) { Copy-Item -Force $androidReleaseAab (Join-Path $androidDir "atelier-android-release.aab") }
    if (Test-Path -LiteralPath $androidDebugApk) { Copy-Item -Force $androidDebugApk (Join-Path $androidDir "atelier-android-debug.apk") }

    Copy-Item -Force $suiteManifest (Join-Path $metaDir "suite-manifest.json")
    if (Test-Path -LiteralPath (Join-Path $expandedSuite "production_go_no_go.metrics.json")) {
        Copy-Item -Force (Join-Path $expandedSuite "production_go_no_go.metrics.json") (Join-Path $metaDir "production_go_no_go.metrics.json")
    }

    $launchInstalledPath = Join-Path $InstallRoot "Launch-Atelier.ps1"
    $launchExeInstalledPath = Join-Path $InstallRoot "Launch-Atelier.exe"
    $desktopIconPath = Join-Path $desktopDir "icon.ico"
    $shortcutIconLocation = ""
    Copy-Item -Force $launchTemplatePath $launchInstalledPath
    if (Test-Path -LiteralPath $launchExeTemplatePath) {
        Copy-Item -Force $launchExeTemplatePath $launchExeInstalledPath
    }
    if (Test-Path -LiteralPath $desktopIconPath) {
        $shortcutIconLocation = $desktopIconPath + ",0"
    } elseif (Test-Path -LiteralPath $launchExeInstalledPath) {
        $shortcutIconLocation = $launchExeInstalledPath + ",0"
    }
    Copy-Item -Force $configTemplatePath (Join-Path $InstallRoot "config.json")

    $desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "Ko's Labyrnth Atelier.lnk"
    $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Ko's Labyrnth"
    Ensure-Directory -Path $startMenuDir
    $startMenuShortcut = Join-Path $startMenuDir "Ko's Labyrnth Atelier.lnk"

    if (Test-Path -LiteralPath $launchExeInstalledPath) {
        Write-Shortcut -ShortcutPath $desktopShortcut -TargetPath $launchExeInstalledPath -Arguments "" -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation
        Write-Shortcut -ShortcutPath $startMenuShortcut -TargetPath $launchExeInstalledPath -Arguments "" -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation
    } else {
        $powershellExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
        $args = "-NoProfile -ExecutionPolicy Bypass -File `"$launchInstalledPath`""
        Write-Shortcut -ShortcutPath $desktopShortcut -TargetPath $powershellExe -Arguments $args -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation
        Write-Shortcut -ShortcutPath $startMenuShortcut -TargetPath $powershellExe -Arguments $args -WorkingDirectory $InstallRoot -IconLocation $shortcutIconLocation
    }

    Write-Host "Install complete."
    Write-Host "Install root: $InstallRoot"
    Write-Host "Desktop shortcut: $desktopShortcut"
    Write-Host "Start menu shortcut: $startMenuShortcut"

    if ($RunAfterInstall) {
        if (Test-Path -LiteralPath $launchExeInstalledPath) {
            Start-Process -FilePath $launchExeInstalledPath | Out-Null
        } else {
            $powershellExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
            & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $launchInstalledPath
        }
    }
} finally {
    if (Test-Path -LiteralPath $tempRoot) {
        Remove-Item -Recurse -Force -LiteralPath $tempRoot
    }
}
