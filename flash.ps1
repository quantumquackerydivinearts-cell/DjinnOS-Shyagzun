# flash.ps1 -- Write build\djinnos.img to a USB drive.
#
# Run as Administrator.  Lists all removable/USB disks so you can
# pick by number rather than guessing \\.\PhysicalDriveN.
#
# Usage:
#   .\flash.ps1                    -- interactive: lists drives, asks which one
#   .\flash.ps1 -DiskNumber 2      -- skip the listing, write to Disk 2
#   .\flash.ps1 -Image path\to.img -- use a different image file

param(
    [int]    $DiskNumber = -1,
    [string] $Image      = "build\djinnos.img"
)

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

$imgPath = Join-Path $PSScriptRoot $Image
if (-not (Test-Path $imgPath)) {
    Write-Host "Image not found: $imgPath" -ForegroundColor Red
    Write-Host "Run .\make_usb.ps1 first to build it." -ForegroundColor Yellow
    exit 1
}

$imgSize = (Get-Item $imgPath).Length
Write-Host ""
Write-Host "Image: $imgPath  ($([math]::Round($imgSize / 1MB, 1)) MiB)" -ForegroundColor Cyan

# ---- List removable / USB disks ----------------------------------------------

$disks = Get-Disk | Where-Object {
    $_.BusType -eq 'USB' -or $_.IsRemovable -eq $true
} | Sort-Object Number

if ($disks.Count -eq 0) {
    Write-Host ""
    Write-Host "No USB / removable disks found.  Plug in the USB drive and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Removable / USB disks:" -ForegroundColor Cyan
foreach ($d in $disks) {
    $sizeMiB = [math]::Round($d.Size / 1MB, 0)
    Write-Host ("  Disk {0}  {1,-30}  {2} MiB  BusType={3}" -f `
        $d.Number, $d.FriendlyName, $sizeMiB, $d.BusType) -ForegroundColor White
}

# ---- Pick target -------------------------------------------------------------

if ($DiskNumber -lt 0) {
    Write-Host ""
    $input = Read-Host "Enter disk NUMBER to flash (Ctrl+C to abort)"
    if (-not ($input -match '^\d+$')) { Write-Host "Aborted."; exit 0 }
    $DiskNumber = [int]$input
}

$target = $disks | Where-Object { $_.Number -eq $DiskNumber }
if ($null -eq $target) {
    Write-Host "Disk $DiskNumber is not in the removable/USB list.  Refusing to continue." -ForegroundColor Red
    exit 1
}

$targetSizeMiB = [math]::Round($target.Size / 1MB, 0)

# Safety: image must be no larger than the target drive.
if ($imgSize -gt $target.Size) {
    Write-Host ""
    Write-Host "Image ($([math]::Round($imgSize/1MB,1)) MiB) is larger than Disk $DiskNumber ($targetSizeMiB MiB)." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Target: Disk $($target.Number) — $($target.FriendlyName) ($targetSizeMiB MiB)" -ForegroundColor Yellow
Write-Host "ALL DATA ON THAT DRIVE WILL BE DESTROYED." -ForegroundColor Red
Write-Host ""
$confirm = Read-Host "Type YES to flash"
if ($confirm -ne "YES") { Write-Host "Aborted."; exit 0 }

# ---- Dismount all volumes on target before writing ---------------------------

$vols = Get-Partition -DiskNumber $target.Number -ErrorAction SilentlyContinue |
        Get-Volume -ErrorAction SilentlyContinue
foreach ($v in $vols) {
    if ($v.DriveLetter) {
        Write-Host "Dismounting $($v.DriveLetter):..." -ForegroundColor DarkGray
        # Lock the volume so Windows releases file handles.
        $mountPoint = "$($v.DriveLetter):"
        try { (New-Object -ComObject Shell.Application).NameSpace(17).ParseName($mountPoint) | Out-Null } catch {}
    }
}

# ---- Write image using pure PowerShell FileStream ----------------------------

Write-Host ""
Write-Host "Writing..." -ForegroundColor Cyan

$src = [System.IO.File]::OpenRead($imgPath)
$dst = [System.IO.File]::Open(
    "\\.\PhysicalDrive$($target.Number)",
    [System.IO.FileMode]::Open,
    [System.IO.FileAccess]::Write,
    [System.IO.FileShare]::None
)

$buf    = New-Object byte[] (4 * 1024 * 1024)   # 4 MiB chunks
$total  = 0
$report = 0

try {
    while ($true) {
        $n = $src.Read($buf, 0, $buf.Length)
        if ($n -le 0) { break }
        $dst.Write($buf, 0, $n)
        $total  += $n
        $report += $n
        if ($report -ge 8MB) {
            $pct = [math]::Round($total * 100 / $imgSize, 0)
            Write-Host "  $([math]::Round($total/1MB, 1)) / $([math]::Round($imgSize/1MB, 1)) MiB  ($pct%)" -ForegroundColor DarkGray
            $report = 0
        }
    }
    $dst.Flush()
} finally {
    $src.Close()
    $dst.Close()
}

Write-Host ""
Write-Host "Done.  $([math]::Round($total/1MB, 1)) MiB written to Disk $($target.Number)." -ForegroundColor Green
Write-Host "Safely eject the drive before booting." -ForegroundColor Cyan
Write-Host ""