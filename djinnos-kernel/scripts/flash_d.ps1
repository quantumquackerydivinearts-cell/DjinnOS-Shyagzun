# DjinnOS — flash boot files to D:
#
# Assumes D: is already a FAT32 volume (USB drive or SD card).
# Builds both binaries and writes:
#   D:\EFI\BOOT\BOOTX64.EFI   ← djinnos-loader
#   D:\kernel.elf              ← djinnos-kernel ELF
#
# No admin rights required — no partitioning, just file copies.
# Run from anywhere; paths are resolved relative to this script.

$ErrorActionPreference = "Stop"

$KERNEL_DIR = Split-Path $PSScriptRoot                        # c:\DjinnOS\djinnos-kernel
$REPO_ROOT  = Split-Path $KERNEL_DIR                          # c:\DjinnOS
$LOADER_DIR = Join-Path $REPO_ROOT "djinnos-loader"           # c:\DjinnOS\djinnos-loader
$DEST       = "D:"

# ── Sanity check ──────────────────────────────────────────────────────────────

if (-not (Test-Path "$DEST\")) {
    Write-Error "D: is not mounted. Plug in the drive and try again."
    exit 1
}

# ── Build loader ──────────────────────────────────────────────────────────────

Write-Host "Building djinnos-loader..." -ForegroundColor Cyan
Push-Location $LOADER_DIR
cargo build --target x86_64-unknown-uefi --release
if ($LASTEXITCODE -ne 0) { Write-Error "Loader build failed"; exit 1 }
Pop-Location

$LOADER_EFI = Join-Path $LOADER_DIR "target\x86_64-unknown-uefi\release\djinnos-loader.efi"
$loaderKiB  = [math]::Round((Get-Item $LOADER_EFI).Length / 1KB)
Write-Host "  OK  $loaderKiB KiB" -ForegroundColor Green

# ── Build kernel ──────────────────────────────────────────────────────────────

Write-Host "Building djinnos-kernel..." -ForegroundColor Cyan
Push-Location $KERNEL_DIR
cargo build --target x86_64-unknown-none --release
if ($LASTEXITCODE -ne 0) { Write-Error "Kernel build failed"; exit 1 }
Pop-Location

$KERNEL_ELF = Join-Path $KERNEL_DIR "target\x86_64-unknown-none\release\djinnos-kernel"
$kernelKiB  = [math]::Round((Get-Item $KERNEL_ELF).Length / 1KB)
Write-Host "  OK  $kernelKiB KiB" -ForegroundColor Green

# ── Copy files ────────────────────────────────────────────────────────────────

Write-Host "Writing to $DEST..." -ForegroundColor Cyan

New-Item -Path "$DEST\EFI\BOOT" -ItemType Directory -Force | Out-Null
Copy-Item $LOADER_EFI "$DEST\EFI\BOOT\BOOTX64.EFI" -Force
Write-Host "  $DEST\EFI\BOOT\BOOTX64.EFI  ($loaderKiB KiB)" -ForegroundColor Green

Copy-Item $KERNEL_ELF "$DEST\kernel.elf" -Force
Write-Host "  $DEST\kernel.elf             ($kernelKiB KiB)" -ForegroundColor Green

# loader.efi at USB root = USB discriminator for auto-install.
# The loader detects USB boot by finding loader.efi in ramdisk (internal ESP never has it).
# It also carries the loader binary so the internal BOOTX64.EFI stays up to date.
Copy-Item $LOADER_EFI "$DEST\loader.efi" -Force
Write-Host "  $DEST\loader.efi             ($loaderKiB KiB)  [ramdisk: USB marker + loader update]" -ForegroundColor Green

# RTL8852AE WiFi firmware — copy from C:\ if present.
# Installed on ESP as rtw8852a.bin so native boots carry it in ramdisk.
$FW_SRC = "C:\rtw8852a_fw.bin"
if (Test-Path $FW_SRC) {
    $fwKiB = [math]::Round((Get-Item $FW_SRC).Length / 1KB)
    Copy-Item $FW_SRC "$DEST\rtw8852a.bin" -Force
    Write-Host "  $DEST\rtw8852a.bin           ($fwKiB KiB)  [ramdisk: WiFi firmware]" -ForegroundColor Green
} else {
    Write-Host "  rtw8852a_fw.bin not found at C:\ -- WiFi firmware not included" -ForegroundColor Yellow
}

Write-Host @"

Done. To boot:
  Eject D: and plug into the HP. F9 at POST -> select the USB device.

To install DjinnOS to the internal SSD (replaces Windows):
  1. Boot from USB as above.
  2. At the Ko shell, type: install
  3. Wait for 'Install complete'. Pull USB. Reboot.
  From then on, boot directly from the SSD — no USB needed.
  To update: reflash this USB, boot from it, run install again.
"@ -ForegroundColor White
