# DjinnOS — launch script
# Builds (if needed) and boots DjinnOS in QEMU.
# UART output appears here; the GPU display opens in a separate QEMU window.

Set-Location $PSScriptRoot

$env:PATH += ";$env:USERPROFILE\.cargo\bin"

Write-Host "DjinnOS" -ForegroundColor Magenta
Write-Host "Building and booting..." -ForegroundColor Cyan

cargo run --release

if ($LASTEXITCODE -ne 0) {
    Write-Host "QEMU exited with code $LASTEXITCODE" -ForegroundColor Yellow
}

Write-Host "DjinnOS session ended." -ForegroundColor DarkGray
Read-Host "Press Enter to close"