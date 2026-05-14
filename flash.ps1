# flash.ps1 — Build DjinnOS and install to a USB / removable drive.
#
# Boot chain: djinnos-loader.efi (UEFI, kernel embedded) -> EFI\BOOT\BOOTX64.EFI
#
# Usage:
#   .\flash.ps1              # build + auto-detect removable drives
#   .\flash.ps1 -Drive D:    # build + install to D:
#   .\flash.ps1 -Test        # build + QEMU OVMF test
#   .\flash.ps1 -NoBuild     # skip build, flash existing artifact
#   .\flash.ps1 -Force       # skip confirmation prompts

param(
    [string] $Drive   = "",
    [switch] $Test,
    [switch] $NoBuild,
    [switch] $Force
)

$ErrorActionPreference = "Stop"
$Root      = $PSScriptRoot
$KernelDir = Join-Path $Root "djinnos-kernel"
$LoaderDir = Join-Path $Root "djinnos-loader"
$EfiArt    = Join-Path $LoaderDir "target\x86_64-unknown-uefi\release\djinnos-loader.efi"
$env:PATH += ";$env:USERPROFILE\.cargo\bin"

$Log = Join-Path $Root "flash.log"
Start-Transcript -Path $Log -Force | Out-Null

function Banner([string]$msg) { Write-Host ""; Write-Host "  === $msg ===" -ForegroundColor Cyan; Write-Host "" }
function Ok([string]$msg)     { Write-Host "  OK  $msg" -ForegroundColor Green }
function Info([string]$msg)   { Write-Host "  ..  $msg" -ForegroundColor DarkGray }
function Warn([string]$msg)   { Write-Host "  !!  $msg" -ForegroundColor Yellow }

function Die([string]$msg) {
    Write-Host ""
    Write-Host "  FAILED: $msg" -ForegroundColor Red
    Write-Host "  Log   : $Log" -ForegroundColor DarkGray
    Write-Host ""
    Stop-Transcript | Out-Null
    exit 1
}

function Ask([string]$prompt) {
    if ($Force) { return }
    $ans = Read-Host "  $prompt [y/N]"
    if ($ans -notmatch '^[Yy]') { Write-Host "  Aborted."; Stop-Transcript | Out-Null; exit 0 }
}

# ── 1. Build ──────────────────────────────────────────────────────────────────

if (-not $NoBuild) {
    Banner "Build"

    Info "kernel  (x86_64-unknown-none --release)"
    Push-Location $KernelDir
    cargo build --target x86_64-unknown-none --release
    $rc = $LASTEXITCODE
    Pop-Location
    if ($rc -ne 0) { Die "Kernel build failed (exit $rc). See above." }
    Ok "Kernel"

    Info "loader  (x86_64-unknown-uefi --release)"
    Push-Location $LoaderDir
    cargo build --release
    $rc = $LASTEXITCODE
    Pop-Location
    if ($rc -ne 0) { Die "Loader build failed (exit $rc). See above." }
    Ok "Loader"
} else {
    Warn "Skipping build (-NoBuild)"
}

if (-not (Test-Path $EfiArt)) {
    Die "EFI artifact missing:`n       $EfiArt`n       Build first (omit -NoBuild)."
}
$efiKiB = [int]((Get-Item $EfiArt).Length / 1024)
Info "Artifact : $EfiArt  ($efiKiB KiB)"

# ── 2. QEMU test ─────────────────────────────────────────────────────────────

if ($Test) {
    Banner "QEMU OVMF test"
    $ovmf  = "C:\Program Files\QEMU\share\edk2-x86_64-code.fd"
    $stage = "$env:TEMP\djinnos_efi_test\EFI\BOOT"
    if (-not (Test-Path $ovmf)) { Die "OVMF not found: $ovmf`n       Install QEMU for Windows." }
    New-Item -Path $stage -ItemType Directory -Force | Out-Null
    Copy-Item $EfiArt "$stage\BOOTX64.EFI" -Force
    Info "Staging: $stage"
    & "C:\Program Files\QEMU\qemu-system-x86_64.exe" `
        -machine q35 -m 512M `
        -drive if=pflash,format=raw,readonly=on,file="$ovmf" `
        -drive "file=fat:rw:$env:TEMP\djinnos_efi_test,format=raw,if=ide,media=disk" `
        -serial stdio -display sdl -no-reboot -no-shutdown
    Stop-Transcript | Out-Null
    exit 0
}

# ── 3. Pick target drive ──────────────────────────────────────────────────────

Banner "Drive"

# Use WMI DriveType 2 (removable) — works regardless of bus type or PS version.
$removable = @(Get-WmiObject Win32_LogicalDisk |
    Where-Object { $_.DriveType -eq 2 } |
    ForEach-Object {
        [PSCustomObject]@{
            Letter = $_.DeviceID
            Label  = if ($_.VolumeName) { $_.VolumeName } else { "(no label)" }
            FS     = if ($_.FileSystem) { $_.FileSystem } else { "unknown" }
            SizeGB = [math]::Round($_.Size / 1GB, 1)
        }
    })

if ($Drive -ne "") {
    # Normalise e / e: / E: -> E:
    $Drive = ($Drive.TrimEnd('\').TrimEnd('/').ToUpper() -replace ':$','') + ':'
    $target = $removable | Where-Object { $_.Letter -eq $Drive }
    if (-not $target) {
        # Check if it exists at all
        $any = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DeviceID -eq $Drive }
        if (-not $any) { Die "Drive $Drive not found." }
        Die "Drive $Drive exists but is not removable (DriveType $($any.DriveType)).`n       flash.ps1 only writes to removable drives."
    }
} else {
    if ($removable.Count -eq 0) {
        Die "No removable drives found.`n       Insert a USB drive, or use -Test for QEMU."
    }
    if ($removable.Count -eq 1) {
        $target = $removable[0]
        Info "Found one removable drive: $($target.Letter)  $($target.Label)  $($target.SizeGB) GB  $($target.FS)"
    } else {
        Write-Host "  Removable drives:" -ForegroundColor White
        for ($i = 0; $i -lt $removable.Count; $i++) {
            $d = $removable[$i]
            Write-Host ("    [{0}]  {1}   {2,-20}  {3,5} GB   {4}" -f ($i+1), $d.Letter, $d.Label, $d.SizeGB, $d.FS)
        }
        Write-Host ""
        $sel = Read-Host "  Select number"
        if ($sel -notmatch '^\d+$') { Write-Host "  Aborted."; Stop-Transcript | Out-Null; exit 0 }
        $idx = [int]$sel - 1
        if ($idx -lt 0 -or $idx -ge $removable.Count) { Die "Invalid selection." }
        $target = $removable[$idx]
    }
    $Drive = $target.Letter
}

# Verify filesystem is FAT-compatible for EFI
if ($target.FS -notin @('FAT','FAT32','exFAT','unknown')) {
    Die "Drive $Drive is $($target.FS).`n       EFI requires FAT / FAT32 / exFAT.`n       Reformat the drive and retry."
}

# ── 4. Confirm and install ────────────────────────────────────────────────────

Write-Host ""
Write-Host "  Drive    : $Drive  ($($target.Label))  $($target.SizeGB) GB  $($target.FS)" -ForegroundColor Yellow
Write-Host "  Installs : $Drive\EFI\BOOT\BOOTX64.EFI" -ForegroundColor Yellow
Write-Host ""
Ask "Flash DjinnOS to $Drive ?"

Banner "Installing"

$bootDir = "$Drive\EFI\BOOT"
New-Item -Path $bootDir -ItemType Directory -Force | Out-Null
Copy-Item $EfiArt "$bootDir\BOOTX64.EFI" -Force

$installed = Get-Item "$bootDir\BOOTX64.EFI"
Ok "Installed $bootDir\BOOTX64.EFI  ($([int]($installed.Length/1024)) KiB)"

# ── 5. Done ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "  Done. Eject $Drive and boot the target machine from USB." -ForegroundColor Green
Write-Host "  Disable Secure Boot if firmware refuses to run unsigned EFI." -ForegroundColor DarkGray
Write-Host "  Full log: $Log" -ForegroundColor DarkGray
Write-Host ""

Stop-Transcript | Out-Null
