# flash.ps1 -- Write build\djinnos.img to a USB drive.
#
# Run as Administrator.
#
# Usage:
#   .\flash.ps1 -Drive D           -- write to the drive mounted as D:
#   .\flash.ps1 -DiskNumber 1      -- write to Disk 1 directly
#   .\flash.ps1 -Image path\to.img -- use a different image file

param(
    [string] $Drive      = "",
    [int]    $DiskNumber = -1,
    [string] $Image      = "build\djinnos.img"
)

Set-Location $PSScriptRoot

$imgPath = Join-Path $PSScriptRoot $Image
if (-not (Test-Path $imgPath)) {
    Write-Host "Image not found: $imgPath" -ForegroundColor Red
    Write-Host "Run .\make_usb.ps1 first." -ForegroundColor Yellow
    exit 1
}
$imgSize = (Get-Item $imgPath).Length
Write-Host "Image: $imgPath  ($([math]::Round($imgSize / 1MB, 1)) MiB)" -ForegroundColor Cyan

# ---- Resolve disk number -----------------------------------------------------

if ($Drive -ne "") {
    $letter = $Drive.TrimEnd(':').ToUpper()
    $part   = Get-Partition | Where-Object { $_.DriveLetter -eq $letter } | Select-Object -First 1
    if ($null -eq $part) {
        Write-Host "No partition found for drive ${letter}:" -ForegroundColor Red
        exit 1
    }
    $DiskNumber = $part.DiskNumber
    Write-Host "Drive ${letter}: -> Disk $DiskNumber" -ForegroundColor DarkGray
}

if ($DiskNumber -lt 0) {
    # No target given — list USB disks and ask.
    $usb = Get-Disk | Where-Object { $_.BusType -eq 'USB' }
    if ($usb.Count -eq 0) {
        Write-Host "No USB disks found. Plug in the drive and try again." -ForegroundColor Yellow
        exit 1
    }
    Write-Host ""
    Write-Host "USB disks:" -ForegroundColor Cyan
    foreach ($d in $usb) {
        Write-Host ("  Disk {0}  {1}  ({2} MiB)" -f $d.Number, $d.FriendlyName, [math]::Round($d.Size/1MB))
    }
    Write-Host ""
    $choice = Read-Host "Enter disk NUMBER (Ctrl+C to abort)"
    if ($choice -notmatch '^\d+$') { Write-Host "Aborted."; exit 0 }
    $DiskNumber = [int]$choice
}

# ---- Confirm target ----------------------------------------------------------

$disk = Get-Disk -Number $DiskNumber -ErrorAction SilentlyContinue
if ($null -eq $disk) {
    Write-Host "Disk $DiskNumber not found." -ForegroundColor Red
    exit 1
}
if ($disk.BusType -ne 'USB') {
    Write-Host "Disk $DiskNumber BusType=$($disk.BusType) -- not a USB drive, refusing." -ForegroundColor Red
    exit 1
}
if ($imgSize -gt $disk.Size) {
    Write-Host "Image ($([math]::Round($imgSize/1MB,1)) MiB) > Disk $DiskNumber ($([math]::Round($disk.Size/1MB)) MiB). Won't fit." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Target : Disk $($disk.Number) -- $($disk.FriendlyName) ($([math]::Round($disk.Size/1MB)) MiB)" -ForegroundColor Yellow
Write-Host "ALL DATA ON THAT DRIVE WILL BE DESTROYED." -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "Type YES to flash"
if ($confirm -ne "YES") { Write-Host "Aborted."; exit 0 }

# ---- Write -------------------------------------------------------------------

Write-Host ""
Write-Host "Writing..." -ForegroundColor Cyan

try {
    $src = [System.IO.File]::OpenRead($imgPath)
} catch {
    Write-Host "Cannot open image: $_" -ForegroundColor Red; exit 1
}

try {
    $dst = [System.IO.File]::Open(
        "\\.\PhysicalDrive$DiskNumber",
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
} catch {
    $src.Close()
    Write-Host "Cannot open Disk $DiskNumber for writing: $_" -ForegroundColor Red
    Write-Host "Make sure you are running as Administrator." -ForegroundColor Yellow
    exit 1
}

$buf    = New-Object byte[] (4 * 1024 * 1024)
$total  = 0
$next   = 8 * 1024 * 1024

try {
    while ($true) {
        $n = $src.Read($buf, 0, $buf.Length)
        if ($n -le 0) { break }
        $dst.Write($buf, 0, $n)
        $total += $n
        if ($total -ge $next) {
            Write-Host ("  {0,5:N1} / {1:N1} MiB" -f ($total/1MB), ($imgSize/1MB)) -ForegroundColor DarkGray
            $next += 8 * 1024 * 1024
        }
    }
    $dst.Flush()
    Write-Host ""
    Write-Host "Done. $([math]::Round($total/1MB,1)) MiB written to Disk $DiskNumber." -ForegroundColor Green
    Write-Host "Eject the drive before booting." -ForegroundColor Cyan
} catch {
    Write-Host "Write error: $_" -ForegroundColor Red
} finally {
    $src.Close()
    $dst.Close()
}