# DjinnOS kernel build script
# Creates disk image then builds the kernel.
# Run from C:\DjinnOS\djinnos-kernel\

$env:PATH += ";$env:USERPROFILE\.cargo\bin"

Write-Host "Building disk image..." -ForegroundColor Cyan
python tools/mkdisk.py disk.img tools/disk
if ($LASTEXITCODE -ne 0) { Write-Error "mkdisk failed"; exit 1 }

Write-Host "Building kernel..." -ForegroundColor Cyan
cargo build --release
if ($LASTEXITCODE -ne 0) { Write-Error "cargo build failed"; exit 1 }

Write-Host "Done. Run with: cargo run --release" -ForegroundColor Green