# deploy.ps1 -- Build DjinnOS and copy boot files onto an existing FAT32 USB.
#
# Does NOT reformat or repartition the drive.  Existing files are untouched
# except for EFI\BOOT\BOOTX64.EFI and KERNEL.ELF which are overwritten.
#
# Usage:
#   .\deploy.ps1              -- build and deploy to D:
#   .\deploy.ps1 -Drive E     -- deploy to a different drive letter

param(
    [string] $Drive = "D"
)

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

$letter = $Drive.TrimEnd(':').ToUpper()
$root   = "${letter}:\"

if (-not (Test-Path $root)) {
    Write-Host "Drive ${letter}: not found." -ForegroundColor Red; exit 1
}

# ---- 1. Build ----------------------------------------------------------------

Write-Host "Building UEFI loader..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\djinnos-loader"
cargo build --release
Pop-Location

Write-Host "Building kernel..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\djinnos-kernel"
cargo build --release --target x86_64-unknown-none
Pop-Location

$loaderSrc = "$PSScriptRoot\djinnos-loader\target\x86_64-unknown-uefi\release\djinnos-loader.efi"
$kernelSrc = "$PSScriptRoot\djinnos-kernel\target\x86_64-unknown-none\release\djinnos-kernel"

# ---- 2. Copy -----------------------------------------------------------------

$efiDir = Join-Path $root "EFI\BOOT"
New-Item -ItemType Directory -Force -Path $efiDir | Out-Null

$loaderDst = Join-Path $efiDir "BOOTX64.EFI"
$kernelDst = Join-Path $root  "KERNEL.ELF"

Write-Host ""
Write-Host "Copying to ${letter}:..." -ForegroundColor Cyan
Copy-Item -Force $loaderSrc $loaderDst
Write-Host "  EFI\BOOT\BOOTX64.EFI  ($([math]::Round((Get-Item $loaderDst).Length/1KB)) KiB)" -ForegroundColor Green
Copy-Item -Force $kernelSrc $kernelDst
Write-Host "  KERNEL.ELF            ($([math]::Round((Get-Item $kernelDst).Length/1MB, 1)) MiB)" -ForegroundColor Green

Write-Host ""
Write-Host "Done. Eject ${letter}: and boot." -ForegroundColor Cyan