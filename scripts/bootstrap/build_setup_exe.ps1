param(
    [string]$OutExePath = "c:\DjinnOS\releases\KoLabyrnth-Setup.exe",
    [ValidateSet("none", "selfsigned", "thumbprint", "pfx")]
    [string]$SignMode = "selfsigned",
    [string]$CertThumbprint = "",
    [string]$PfxPath = "",
    [string]$PfxPassword = "",
    [string]$TimestampServer = "",
    [switch]$KeepTemp
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

function Find-CodeSignCertByThumbprint {
    param([Parameter(Mandatory = $true)][string]$Thumbprint)
    $normalized = $Thumbprint.Replace(" ", "").ToUpperInvariant()
    $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Thumbprint.ToUpperInvariant() -eq $normalized } |
        Select-Object -First 1
    if ($cert) { return $cert }
    $cert = Get-ChildItem Cert:\LocalMachine\My -CodeSigningCert |
        Where-Object { $_.Thumbprint.ToUpperInvariant() -eq $normalized } |
        Select-Object -First 1
    return $cert
}

$bootstrapRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path (Split-Path $bootstrapRoot -Parent) -Parent
$wizardCmd = Join-Path $bootstrapRoot "Setup-Wizard.cmd"
$wizardPs1 = Join-Path $bootstrapRoot "Setup-Wizard.ps1"
$installerPs1 = Join-Path $bootstrapRoot "Install-Atelier.ps1"
$launcherPs1 = Join-Path $bootstrapRoot "Launch-Atelier.ps1"
$launcherExe = Join-Path $bootstrapRoot "Launch-Atelier.exe"
$launcherBuilder = Join-Path $bootstrapRoot "build_launcher_exe.ps1"
$iconPath = Join-Path $repoRoot "apps\atelier-desktop\public\icon.ico"
$configTemplate = Join-Path $bootstrapRoot "config.template.json"
$readme = Join-Path $bootstrapRoot "README-quickstart.txt"

Require-Path -Path $wizardCmd
Require-Path -Path $wizardPs1
Require-Path -Path $installerPs1
Require-Path -Path $launcherPs1
Require-Path -Path $iconPath
Require-Path -Path $configTemplate
Require-Path -Path $readme

$iexpress = Join-Path $env:WINDIR "System32\iexpress.exe"
Require-Path -Path $iexpress

$outDir = Split-Path -Parent $OutExePath
Ensure-Directory -Path $outDir

$tempRoot = Join-Path $env:TEMP ("atelier-setup-exe-" + [guid]::NewGuid().ToString("N"))
$stageDir = Join-Path $tempRoot "stage"
Ensure-Directory -Path $stageDir

try {
    if (Test-Path -LiteralPath $launcherBuilder) {
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $launcherBuilder -OutExePath $launcherExe -IconPath $iconPath
        } catch {
            Write-Warning ("launch_exe_build_failed: " + $_.Exception.Message)
        }
    }

    Copy-Item -Force $wizardCmd (Join-Path $stageDir "Setup-Wizard.cmd")
    Copy-Item -Force $wizardPs1 (Join-Path $stageDir "Setup-Wizard.ps1")
    Copy-Item -Force $installerPs1 (Join-Path $stageDir "Install-Atelier.ps1")
    Copy-Item -Force $launcherPs1 (Join-Path $stageDir "Launch-Atelier.ps1")
    Copy-Item -Force $iconPath (Join-Path $stageDir "icon.ico")
    Copy-Item -Force $configTemplate (Join-Path $stageDir "config.template.json")
    Copy-Item -Force $readme (Join-Path $stageDir "README-quickstart.txt")
    if (Test-Path -LiteralPath $launcherExe) {
        Copy-Item -Force $launcherExe (Join-Path $stageDir "Launch-Atelier.exe")
    }

    $runSetupCmd = Join-Path $stageDir "RunSetup.cmd"
    @"
@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\Setup-Wizard.ps1"
endlocal
"@ | Set-Content -Encoding ASCII -LiteralPath $runSetupCmd

    if (Test-Path -LiteralPath $OutExePath) {
        Remove-Item -Force -LiteralPath $OutExePath
    }

    $sedPath = Join-Path $tempRoot "setup.sed"
    $fileNames = @(
        "Setup-Wizard.cmd",
        "Setup-Wizard.ps1",
        "Install-Atelier.ps1",
        "Launch-Atelier.ps1",
        "icon.ico",
        "config.template.json",
        "README-quickstart.txt",
        "RunSetup.cmd"
    )
    if (Test-Path -LiteralPath (Join-Path $stageDir "Launch-Atelier.exe")) {
        $fileNames += "Launch-Atelier.exe"
    }
    $fileEntries = @()
    $sourceEntries = @()
    $stringEntries = @()
    for ($i = 0; $i -lt $fileNames.Count; $i++) {
        $key = "FILE$i"
        $fileEntries += "$key=$($fileNames[$i])"
        $sourceEntries += "%$key%="
        $stringEntries += "$key=`"$($fileNames[$i])`""
    }
    $fileEntriesText = ($fileEntries -join [Environment]::NewLine)
    $sourceEntriesText = ($sourceEntries -join [Environment]::NewLine)
    $stringEntriesText = ($stringEntries -join [Environment]::NewLine)

    @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=0
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=Ko's Labyrnth Atelier setup is ready.
TargetName=$OutExePath
FriendlyName=Ko's Labyrnth Atelier Setup
AppLaunched=RunSetup.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SelfDelete=0
SourceFiles=SourceFiles
$fileEntriesText
[SourceFiles]
SourceFiles0=$stageDir
[SourceFiles0]
$sourceEntriesText
[Strings]
$stringEntriesText
"@ | Set-Content -Encoding ASCII -LiteralPath $sedPath

    Write-Host ("iexpress_sed: " + $sedPath)
    & $iexpress /N /Q $sedPath
    if (Test-Path variable:LASTEXITCODE) {
        if ($LASTEXITCODE -ne 0) {
            throw "IExpress failed with exit code $LASTEXITCODE"
        }
    }
    $attempts = 0
    while ((-not (Test-Path -LiteralPath $OutExePath)) -and ($attempts -lt 20)) {
        Start-Sleep -Milliseconds 500
        $attempts++
    }
    if (-not (Test-Path -LiteralPath $OutExePath)) {
        Write-Host "IExpress did not produce expected target. Stage directory contents:"
        Get-ChildItem -LiteralPath $stageDir -Force | Select-Object Name,Length,LastWriteTime
        throw "Installer EXE was not produced at expected path: $OutExePath"
    }

    $signCert = $null
    if ($SignMode -eq "selfsigned") {
        $signCert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=Ko's Labyrnth Local Installer Signer" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -NotAfter (Get-Date).AddYears(2)
    } elseif ($SignMode -eq "thumbprint") {
        if ([string]::IsNullOrWhiteSpace($CertThumbprint)) {
            throw "SignMode=thumbprint requires -CertThumbprint"
        }
        $signCert = Find-CodeSignCertByThumbprint -Thumbprint $CertThumbprint
        if (-not $signCert) {
            throw "Code-signing cert not found for thumbprint: $CertThumbprint"
        }
    } elseif ($SignMode -eq "pfx") {
        if ([string]::IsNullOrWhiteSpace($PfxPath)) {
            throw "SignMode=pfx requires -PfxPath"
        }
        Require-Path -Path $PfxPath
        if ([string]::IsNullOrWhiteSpace($PfxPassword)) {
            throw "SignMode=pfx requires -PfxPassword"
        }
        $secure = ConvertTo-SecureString -String $PfxPassword -AsPlainText -Force
        $imported = Import-PfxCertificate -FilePath $PfxPath -Password $secure -CertStoreLocation "Cert:\CurrentUser\My"
        $signCert = $imported | Select-Object -First 1
        if (-not $signCert) {
            throw "Failed to import PFX cert from $PfxPath"
        }
    }

    if ($SignMode -ne "none") {
        if ([string]::IsNullOrWhiteSpace($TimestampServer)) {
            Set-AuthenticodeSignature -FilePath $OutExePath -Certificate $signCert | Out-Null
        } else {
            Set-AuthenticodeSignature -FilePath $OutExePath -Certificate $signCert -TimestampServer $TimestampServer | Out-Null
        }
    }

    $sig = Get-AuthenticodeSignature -FilePath $OutExePath
    Write-Host ("installer_exe: " + $OutExePath)
    Write-Host ("signature_status: " + $sig.Status)
    if ($sig.SignerCertificate) {
        Write-Host ("signer_subject: " + $sig.SignerCertificate.Subject)
        Write-Host ("signer_thumbprint: " + $sig.SignerCertificate.Thumbprint)
    }
} finally {
    if ((-not $KeepTemp) -and (Test-Path -LiteralPath $tempRoot)) {
        Remove-Item -Recurse -Force -LiteralPath $tempRoot
    }
}
