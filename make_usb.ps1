# make_usb.ps1 -- Build DjinnOS and write a bootable USB image.
#
# Requirements:
#   - Rust (rustup target add x86_64-unknown-uefi x86_64-unknown-none)
#   - WSL with: apt install dosfstools mtools gdisk
#
# Usage:
#   .\make_usb.ps1               -- build image to build\djinnos.img
#   .\make_usb.ps1 -Device \\.\PhysicalDrive2   -- also flash to USB (run as Admin)

param(
    [string]$Device   = "",
    [string]$OutImage = "build\djinnos.img"
)

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path "$PSScriptRoot\build" | Out-Null

# ---- 1. Build UEFI loader ----------------------------------------------------
Write-Host "Building UEFI loader (x86_64-unknown-uefi)..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\djinnos-loader"
cargo build --release
$loaderOk = $LASTEXITCODE
Pop-Location
if ($loaderOk -ne 0) { Write-Error "Loader build failed"; exit 1 }
$loaderPath = "$PSScriptRoot\djinnos-loader\target\x86_64-unknown-uefi\release\djinnos-loader.efi"

# ---- 2. Build kernel (x86_64-unknown-none) -----------------------------------
Write-Host "Building kernel (x86_64-unknown-none)..." -ForegroundColor Cyan
Push-Location "$PSScriptRoot\djinnos-kernel"
cargo build --release --target x86_64-unknown-none
$kernelOk = $LASTEXITCODE
Pop-Location
if ($kernelOk -ne 0) { Write-Error "Kernel build failed"; exit 1 }
$kernelPath = "$PSScriptRoot\djinnos-kernel\target\x86_64-unknown-none\release\djinnos-kernel"

Write-Host "Loader: $loaderPath" -ForegroundColor Green
Write-Host "Kernel: $kernelPath" -ForegroundColor Green

# ---- 3. Create disk image with Python (no WSL required) ---------------------
Write-Host "Creating bootable disk image..." -ForegroundColor Cyan

$imgFull   = "$PSScriptRoot\$OutImage"
$makeImg   = "$PSScriptRoot\make_img.py"

python $makeImg $loaderPath $kernelPath $imgFull
if ($LASTEXITCODE -ne 0) { Write-Error "Disk image creation failed"; exit 1 }

$sizeMiB = [math]::Round((Get-Item $imgFull).Length / 1MB, 1)
Write-Host ""
Write-Host "Image ready: $imgFull  ($sizeMiB MiB)" -ForegroundColor Green

# ---- 4. Optional: flash to USB -----------------------------------------------
if ($Device -ne "") {
    Write-Host ""
    Write-Host "About to write to: $Device" -ForegroundColor Yellow
    Write-Host "ALL DATA ON THAT DRIVE WILL BE DESTROYED." -ForegroundColor Red
    $ok = Read-Host "Type YES to confirm"
    if ($ok -ne "YES") { Write-Host "Aborted."; exit 0 }
    # Use dd from WSL to write to the physical device
    $imgWsl = (& wsl wslpath -u ($imgFull -replace '\\','/')).Trim()
    $sh = "$env:TEMP\djinnos_flash.sh"
    $shWsl = (& wsl wslpath -u ($sh -replace '\\','/')).Trim()
    [System.IO.File]::WriteAllText($sh,
        "dd if=`"$imgWsl`" of=`"$Device`" bs=4M status=progress oflag=sync`n",
        [System.Text.UTF8Encoding]::new($false))
    & wsl bash "$shWsl"
    Write-Host "USB written. Safely eject before booting." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "To flash to USB (run as Administrator):" -ForegroundColor Cyan
    Write-Host "  .\make_usb.ps1 -Device \\.\PhysicalDriveN"
    Write-Host "  (find N in Disk Management -- confirm it is your USB, not your system disk)"
    Write-Host ""
    Write-Host "To test in QEMU (needs OVMF.fd from ovmf package):" -ForegroundColor Cyan
    Write-Host "  qemu-system-x86_64 -machine q35 -bios OVMF.fd -m 512M \`"
    Write-Host "    -drive file=build\djinnos.img,format=raw,if=virtio \`"
    Write-Host "    -device e1000,netdev=net0 \`"
    Write-Host "    -netdev user,id=net0,hostfwd=tcp::9000-:9000,hostfwd=tcp::8888-:8888 \`"
    Write-Host "    -serial stdio"
}