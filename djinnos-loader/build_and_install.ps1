# Build DjinnOS kernel + UEFI loader, then install to a target drive.
#
# Usage:
#   .\build_and_install.ps1           # build only
#   .\build_and_install.ps1 D:        # build + install to D:
#   .\build_and_install.ps1 D: test   # build + install + QEMU OVMF test

param(
    [string]$Drive = "",
    [string]$Mode  = ""
)

$ErrorActionPreference = "Stop"
$env:PATH += ";$env:USERPROFILE\.cargo\bin"

# ── 1. Build kernel ───────────────────────────────────────────────────────────
Write-Host "Building kernel..."
Push-Location (Join-Path $PSScriptRoot "..\djinnos-kernel")
cargo build --target x86_64-unknown-none --release
if ($LASTEXITCODE -ne 0) { exit 1 }
Pop-Location

# ── 2. Build loader (embeds kernel) ──────────────────────────────────────────
Write-Host "Building UEFI loader..."
Push-Location $PSScriptRoot
cargo build --release
if ($LASTEXITCODE -ne 0) { exit 1 }
Pop-Location

$EFI = Join-Path $PSScriptRoot "target\x86_64-unknown-uefi\release\djinnos-loader.efi"
Write-Host "Built: $EFI ($([int]((Get-Item $EFI).Length / 1024)) KiB)"

# ── 3. Install to drive ───────────────────────────────────────────────────────
if ($Drive) {
    $boot = "$Drive\EFI\BOOT"
    New-Item -Path $boot -ItemType Directory -Force | Out-Null
    Copy-Item $EFI "$boot\BOOTX64.EFI" -Force
    Write-Host "Installed to $boot\BOOTX64.EFI"
}

# ── 4. Optional QEMU OVMF test ────────────────────────────────────────────────
if ($Mode -eq "test") {
    $ovmf    = "C:\Program Files\QEMU\share\edk2-x86_64-code.fd"
    $efi_dir = "$env:TEMP\djinnos_efi_test"
    $tboot   = "$efi_dir\EFI\BOOT"
    New-Item -Path $tboot -ItemType Directory -Force | Out-Null
    Copy-Item $EFI "$tboot\BOOTX64.EFI"

    Write-Host "Launching QEMU with OVMF..."
    & "C:\Program Files\QEMU\qemu-system-x86_64.exe" `
        -machine q35 -m 256M `
        -drive if=pflash,format=raw,readonly=on,file="$ovmf" `
        -drive file=fat:rw:$efi_dir,format=raw,if=ide,media=disk `
        -serial stdio -display none `
        -no-reboot -no-shutdown
}
