# Build and optionally run DjinnOS x86_64 kernel.
#
# Usage:
#   .\build_x86.ps1         -- build only (release)
#   .\build_x86.ps1 run     -- build + run in QEMU
#   .\build_x86.ps1 debug   -- build debug + run in QEMU

$ErrorActionPreference = "Stop"
$env:PATH += ";$env:USERPROFILE\.cargo\bin"

$Profile = if ($args[0] -eq "debug") { "" } else { "--release" }
$SubDir  = if ($args[0] -eq "debug") { "debug" } else { "release" }

cargo build --target x86_64-unknown-none $Profile
if ($LASTEXITCODE -ne 0) { exit 1 }

$ELF = "target\x86_64-unknown-none\$SubDir\djinnos-kernel"
$BIN = "target\x86_64-unknown-none\$SubDir\djinnos-kernel.bin"

# Extract flat binary (required for QEMU multiboot1 a.out-kludge loading)
rust-objcopy -O binary $ELF $BIN

Write-Host "Built: $BIN ($([int](Get-Item $BIN).Length / 1024) KiB)"

if ($args[0] -eq "run" -or $args[0] -eq "debug") {
    $QEMU = "C:\Program Files\QEMU\qemu-system-x86_64.exe"
    if (-not (Test-Path $QEMU)) {
        Write-Error "QEMU not found at $QEMU"
        exit 1
    }
    & $QEMU `
        -machine q35 `
        -m 128M `
        -serial stdio `
        -display none `
        -kernel $BIN `
        -device ich9-intel-hda `
        -device hda-output `
        -no-reboot `
        -no-shutdown
}