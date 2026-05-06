# DjinnOS USB boot drive setup
#
# Partitions the target USB-C drive with:
#   Partition 1 — FAT32 EFI System Partition (~256 MiB)
#                 holds GRUB EFI + kernel ELF + grub.cfg
#   Partition 2 — Raw Sa filesystem (rest of drive)
#                 holds kobra.elf and other user binaries
#
# Requirements (must be installed and on PATH):
#   grub-install  — from GRUB2 for Windows or via MSYS2/Cygwin
#   grub-mkimage  — same package
#   mformat       — from mtools (for formatting FAT without Admin rights)
#
# If grub tools are not available on Windows, run the equivalent steps
# in a Linux environment (WSL when available, or a live Linux USB).
#
# Usage:
#   .\make_usb.ps1 <DiskNumber>
#
# Find your USB drive's disk number with:
#   Get-Disk | Select-Object Number, FriendlyName, Size, PartitionStyle
#
# SAFETY: double-check the disk number before running — this ERASES the drive.

param(
    [Parameter(Mandatory=$true)]
    [int]$DiskNumber
)

$ErrorActionPreference = "Stop"
$env:PATH += ";$env:USERPROFILE\.cargo\bin"

# ── Verify target disk ─────────────────────────────────────────────────────────
$disk = Get-Disk -Number $DiskNumber -ErrorAction SilentlyContinue
if (-not $disk) {
    Write-Error "Disk $DiskNumber not found.  Run: Get-Disk | Select Number, FriendlyName, Size"
    exit 1
}
Write-Host "Target disk: [$DiskNumber] $($disk.FriendlyName)  $([int]($disk.Size / 1GB)) GiB"
$confirm = Read-Host "Type YES to erase this disk and create DjinnOS partitions"
if ($confirm -ne "YES") { Write-Host "Aborted."; exit 0 }

# ── Build the kernel ELF (multiboot2, 64-bit) ─────────────────────────────────
Write-Host "`nBuilding kernel..."
Set-Location (Split-Path $PSScriptRoot)
cargo build --target x86_64-unknown-none --release
if ($LASTEXITCODE -ne 0) { Write-Error "Kernel build failed"; exit 1 }
$KERNEL_ELF = "target\x86_64-unknown-none\release\djinnos-kernel"
Write-Host "Kernel: $KERNEL_ELF ($([int]((Get-Item $KERNEL_ELF).Length / 1024)) KiB)"

# ── Partition the drive ────────────────────────────────────────────────────────
Write-Host "`nPartitioning disk $DiskNumber..."
$diskpartScript = @"
select disk $DiskNumber
clean
convert gpt
create partition efi size=256
format quick fs=fat32 label="DJINNOS_EFI"
assign letter=Z
create partition primary
format quick fs=exfat label="DJINNOS_SA"
assign letter=Y
"@
$diskpartScript | diskpart

# Wait for drive letters to appear
Start-Sleep -Seconds 3

# ── Install GRUB to the EFI partition ─────────────────────────────────────────
Write-Host "`nInstalling GRUB..."
$efi = "Z:"
$boot_dir = "$efi\EFI\BOOT"
New-Item -Path $boot_dir -ItemType Directory -Force | Out-Null
New-Item -Path "$efi\djinnos"   -ItemType Directory -Force | Out-Null

# If grub-mkimage is available, generate a minimal EFI stub.
# Otherwise, provide instructions for Linux-based GRUB install.
if (Get-Command grub-mkimage -ErrorAction SilentlyContinue) {
    grub-mkimage --format=x86_64-efi `
                 --output="$boot_dir\BOOTX64.EFI" `
                 --prefix="/djinnos/grub" `
                 part_gpt fat normal multiboot2 echo ls video gfxterm
    New-Item -Path "$efi\djinnos\grub" -ItemType Directory -Force | Out-Null
} else {
    Write-Host @"

  grub-mkimage not found on this system.
  To complete the GRUB install, run from a Linux environment:

    sudo grub-install --target=x86_64-efi \
         --efi-directory=/mnt/efi \
         --boot-directory=/mnt/efi/djinnos \
         --removable

  where /mnt/efi is the mounted EFI partition (Z: on this machine).
"@
}

# ── Copy kernel and write grub.cfg ────────────────────────────────────────────
Copy-Item $KERNEL_ELF "$efi\djinnos\kernel.elf"
Write-Host "Kernel copied to $efi\djinnos\kernel.elf"

@"
set timeout=3
set default=0

menuentry "DjinnOS" {
    insmod multiboot2
    insmod gfxterm
    set gfxmode=1280x800x32,1920x1080x32,auto
    terminal_output gfxterm
    multiboot2 /djinnos/kernel.elf
    boot
}
"@ | Out-File "$efi\djinnos\grub\grub.cfg" -Encoding ascii
Write-Host "grub.cfg written"

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host @"

Done.  Boot order:
  1. Plug the USB drive into the target machine.
  2. Enter firmware (F2 / F12 / DEL at POST) → Boot from USB.
  3. GRUB menu appears → select DjinnOS.
  4. Ko shell renders on screen; PS/2 keyboard is active.

QEMU test (no framebuffer, serial mode):
  .\build_x86.ps1 run
"@
