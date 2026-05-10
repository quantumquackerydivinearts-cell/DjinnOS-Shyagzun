# deploy.ps1 — Non-destructive DjinnOS kernel deploy to existing USB
#
# Copies the built kernel ELF to a USB drive's FAT partition.
# Does NOT reformat, repartition, or erase anything.
# Coexists with existing bootloaders (Windows Boot Manager, etc.).
#
# Usage:
#   .\deploy.ps1               -- build + auto-detect USB FAT volume
#   .\deploy.ps1 -Drive E      -- target specific drive letter
#   .\deploy.ps1 -NoBuild      -- skip build, use existing binary
#   .\deploy.ps1 -Drive E -NoBuild

param(
    [string]$Drive  = "",
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path $MyInvocation.MyCommand.Path

# ── Build ─────────────────────────────────────────────────────────────────────

if (-not $NoBuild) {
    Write-Host "Building x86_64 release kernel..."
    Push-Location $ScriptDir
    cargo build --target x86_64-unknown-none --release
    if ($LASTEXITCODE -ne 0) { Write-Error "Build failed"; exit 1 }
    Pop-Location
}

$KernelELF = Join-Path $ScriptDir "target\x86_64-unknown-none\release\djinnos-kernel"
if (-not (Test-Path $KernelELF)) {
    Write-Error "Kernel ELF not found at $KernelELF — run without -NoBuild first"
    exit 1
}
$KernelKiB = [int]((Get-Item $KernelELF).Length / 1024)
Write-Host "Kernel: $KernelELF  ($KernelKiB KiB)"

# ── Find target drive ─────────────────────────────────────────────────────────

if ($Drive -eq "") {
    # Auto-detect: find FAT/FAT32 volumes on USB-bus disks.
    $usbDisks = Get-Disk | Where-Object { $_.BusType -eq "USB" }
    if (-not $usbDisks) {
        Write-Error "No USB disk found.  Plug in the drive, or specify -Drive <letter>"
        exit 1
    }
    $candidates = @()
    foreach ($disk in $usbDisks) {
        $parts = Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue
        foreach ($p in $parts) {
            $vol = Get-Volume -Partition $p -ErrorAction SilentlyContinue
            if ($vol -and ($vol.FileSystem -eq "FAT32" -or $vol.FileSystem -eq "FAT") `
                       -and $vol.DriveLetter) {
                $candidates += $vol.DriveLetter
            }
        }
    }
    if ($candidates.Count -eq 0) {
        Write-Error "No FAT/FAT32 volume found on USB disks.  Use -Drive <letter> to specify manually."
        exit 1
    }
    if ($candidates.Count -gt 1) {
        Write-Host "Multiple USB FAT volumes found: $($candidates -join ', ')"
        Write-Error "Ambiguous target — specify -Drive <letter>"
        exit 1
    }
    $Drive = $candidates[0]
}

$Root = "$($Drive.TrimEnd(':')):"
if (-not (Test-Path "$Root\")) {
    Write-Error "Drive $Root not accessible"
    exit 1
}

$vol = Get-Volume -DriveLetter $Drive.TrimEnd(':') -ErrorAction SilentlyContinue
Write-Host "Target: $Root  ($($vol.FileSystem)  '$($vol.FileSystemLabel)'  $([int]($vol.Size/1MB)) MiB)"

# ── Safety: refuse to touch internal disks ────────────────────────────────────

$driveLetter = $Drive.TrimEnd(':')
$partition   = Get-Partition -DriveLetter $driveLetter -ErrorAction SilentlyContinue
if ($partition) {
    $disk = Get-Disk -Number $partition.DiskNumber
    if ($disk.BusType -ne "USB") {
        Write-Error "Drive $Root is on a $($disk.BusType) disk, not USB.  Aborting."
        exit 1
    }
}

# ── Deploy ────────────────────────────────────────────────────────────────────

$DjinnDir = "$Root\djinnos"
$GrubDir  = "$DjinnDir\grub"

New-Item -Path $DjinnDir -ItemType Directory -Force | Out-Null

# Kernel ELF
$dest = "$DjinnDir\kernel.elf"
Copy-Item -Path $KernelELF -Destination $dest -Force
Write-Host "Copied kernel  ->  $dest"

# grub.cfg — write if djinnos\grub exists, or create it if no cfg present yet
$needCfg = (Test-Path $GrubDir) -or (-not (Test-Path "$DjinnDir\grub\grub.cfg"))
if (-not (Test-Path $GrubDir)) { New-Item -Path $GrubDir -ItemType Directory -Force | Out-Null }

$cfgPath = "$GrubDir\grub.cfg"
if (-not (Test-Path $cfgPath)) {
    @"
set timeout=3
set default=0

menuentry "DjinnOS" {
    insmod multiboot2
    insmod gfxterm
    set gfxmode=1920x1080x32,1280x800x32,auto
    terminal_output gfxterm
    multiboot2 /djinnos/kernel.elf
    boot
}
"@ | Out-File $cfgPath -Encoding ascii
    Write-Host "Wrote grub.cfg ->  $cfgPath"
} else {
    Write-Host "grub.cfg exists, left unchanged  ($cfgPath)"
}

# Report whether a bootloader is present
$efiStub = "$Root\EFI\BOOT\BOOTX64.EFI"
if (Test-Path $efiStub) {
    Write-Host "UEFI stub found: $efiStub  -- bootloader already present."
} else {
    Write-Host ""
    Write-Host "  NOTE: No BOOTX64.EFI found at $Root\EFI\BOOT\"
    Write-Host "  The kernel is deployed but the drive is not yet bootable."
    Write-Host "  To install GRUB without erasing the drive, run from MSYS2:"
    Write-Host ""
    Write-Host "    pacman -S mingw-w64-x86_64-grub"
    Write-Host "    grub-install --target=x86_64-efi --efi-directory=$Root \"
    Write-Host "                 --boot-directory=$Root\djinnos --removable --no-nvram"
    Write-Host ""
    Write-Host "  This adds EFI\BOOT\BOOTX64.EFI without touching anything else on the drive."
}

# ── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Done.  Kernel deployed to $Root\djinnos\kernel.elf"
Write-Host ""
Write-Host "Boot sequence:"
Write-Host "  1. Plug USB into Envy"
Write-Host "  2. F9 at POST (HP boot menu) -> select the USB"
Write-Host "  3. GRUB loads -> DjinnOS -> Ko"