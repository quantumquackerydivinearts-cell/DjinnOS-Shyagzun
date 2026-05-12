# DjinnOS USB boot drive setup — UEFI loader path (no GRUB required)
#
# Layout written to the USB EFI partition (FAT32, GPT):
#   EFI\BOOT\BOOTX64.EFI   ← djinnos-loader.efi
#   kernel.elf              ← djinnos-kernel ELF (root of partition)
#
# The djinnos-loader IS the EFI bootloader. It reads kernel.elf directly
# from the root of the FAT32 partition via raw BlockIo, then jumps to it.
# No GRUB, no multiboot, no extra tooling required.
#
# Requirements:
#   - Run as Administrator (diskpart needs it)
#   - Rust toolchain with x86_64-unknown-uefi and x86_64-unknown-none targets
#
# Usage:
#   .\make_usb.ps1 <DiskNumber>
#
#   Find your USB disk number first:
#   Get-Disk | Select-Object Number, FriendlyName, Size
#
# HP Envy / Secure Boot:
#   Before booting, disable Secure Boot in HP BIOS:
#   F10 at POST → Security → Secure Boot → Disabled → F10 Save & Exit
#   Then F9 at POST to select the USB boot device.
#
# SAFETY: this ERASES the target disk. Double-check the number.

param(
    [Parameter(Mandatory=$true)]
    [int]$DiskNumber
)

$ErrorActionPreference = "Stop"
$ROOT      = Split-Path $PSScriptRoot             # c:\DjinnOS\djinnos-kernel
$REPO_ROOT = Split-Path $ROOT                    # c:\DjinnOS

# ── Confirm target ─────────────────────────────────────────────────────────────

$disk = Get-Disk -Number $DiskNumber -ErrorAction SilentlyContinue
if (-not $disk) {
    Write-Error "Disk $DiskNumber not found.  Run: Get-Disk | Select Number, FriendlyName, Size"
    exit 1
}
$gb = [math]::Round($disk.Size / 1GB, 1)
Write-Host ""
Write-Host "  Target : [$DiskNumber] $($disk.FriendlyName)  ($gb GiB)" -ForegroundColor Yellow
Write-Host "  Action : erase + GPT + 256 MiB FAT32 EFI partition" -ForegroundColor Yellow
Write-Host ""
$confirm = Read-Host "Type YES to continue"
if ($confirm -ne "YES") { Write-Host "Aborted."; exit 0 }

# ── Build loader (UEFI EFI application) ───────────────────────────────────────

Write-Host "`nBuilding djinnos-loader..." -ForegroundColor Cyan
$LOADER_DIR = Join-Path $REPO_ROOT "djinnos-loader"
Push-Location $LOADER_DIR
cargo build --target x86_64-unknown-uefi --release
if ($LASTEXITCODE -ne 0) { Write-Error "Loader build failed"; exit 1 }
Pop-Location

$LOADER_EFI = Join-Path $LOADER_DIR "target\x86_64-unknown-uefi\release\djinnos-loader.efi"
if (-not (Test-Path $LOADER_EFI)) {
    Write-Error "Loader EFI not found at: $LOADER_EFI"
    exit 1
}
$loaderKiB = [math]::Round((Get-Item $LOADER_EFI).Length / 1KB)
Write-Host "  Loader : $loaderKiB KiB" -ForegroundColor Green

# ── Build kernel (bare-metal ELF) ─────────────────────────────────────────────

Write-Host "`nBuilding djinnos-kernel..." -ForegroundColor Cyan
Push-Location $ROOT
cargo build --target x86_64-unknown-none --release
if ($LASTEXITCODE -ne 0) { Write-Error "Kernel build failed"; exit 1 }
Pop-Location

$KERNEL_ELF = Join-Path $ROOT "target\x86_64-unknown-none\release\djinnos-kernel"
if (-not (Test-Path $KERNEL_ELF)) {
    Write-Error "Kernel ELF not found at: $KERNEL_ELF"
    exit 1
}
$kernelKiB = [math]::Round((Get-Item $KERNEL_ELF).Length / 1KB)
Write-Host "  Kernel : $kernelKiB KiB" -ForegroundColor Green

# ── Partition the drive ────────────────────────────────────────────────────────

Write-Host "`nPartitioning disk $DiskNumber (diskpart)..." -ForegroundColor Cyan

$dp = @"
select disk $DiskNumber
clean
convert gpt
create partition efi size=256
format quick fs=fat32 label="DJINNOS"
assign letter=Z
"@

$dp | diskpart | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Error "diskpart failed"; exit 1 }

# Give Windows a moment to mount the new volume.
Start-Sleep -Seconds 4

if (-not (Test-Path "Z:\")) {
    Write-Error "EFI partition did not mount as Z:. Check disk number and try again."
    exit 1
}

# ── Write boot files ───────────────────────────────────────────────────────────

Write-Host "`nWriting boot files..." -ForegroundColor Cyan

New-Item -Path "Z:\EFI\BOOT" -ItemType Directory -Force | Out-Null

# Loader becomes the EFI boot application.
Copy-Item $LOADER_EFI "Z:\EFI\BOOT\BOOTX64.EFI"
Write-Host "  Z:\EFI\BOOT\BOOTX64.EFI  ($loaderKiB KiB)" -ForegroundColor Green

# Kernel sits at the root — djinnos-loader scans for KERNEL.ELF (FAT32 8.3 name).
Copy-Item $KERNEL_ELF "Z:\kernel.elf"
Write-Host "  Z:\kernel.elf             ($kernelKiB KiB)" -ForegroundColor Green

# ── Verify ────────────────────────────────────────────────────────────────────

Write-Host ""
Get-ChildItem "Z:\" -Recurse | Select-Object FullName, Length | Format-Table -AutoSize

# ── Dismount ──────────────────────────────────────────────────────────────────

Write-Host "Dismounting Z:..." -ForegroundColor Cyan
$dpDismount = "select disk $DiskNumber`nremove letter=Z"
$dpDismount | diskpart | Out-Null

# ── Instructions ──────────────────────────────────────────────────────────────

Write-Host @"

Done.

HP Envy boot steps
──────────────────
1. Plug the USB drive in.

2. Disable Secure Boot (one-time):
     Power on → F10 (BIOS Setup)
     Security → Secure Boot Configuration → Secure Boot → Disabled
     F10 → Save and Exit

3. Boot from USB:
     Power on → F9 (Boot Menu) → select the USB device

4. The loader prints to both screen and COM1 serial (38400 baud).
   On screen: flashes green briefly, then hands off to the kernel.
   Serial log shows: GOP ok / RSDP ok / kernel read ok / entry=...

5. Ko shell should appear. Run 'lspci' to see the PCI device list
   and confirm the WiFi chipset line from the UART log.

To rebuild and reflash without repartitioning:
  .\make_usb.ps1 <DiskNumber>   (repartitions each time — safe, just slower)

"@ -ForegroundColor White
