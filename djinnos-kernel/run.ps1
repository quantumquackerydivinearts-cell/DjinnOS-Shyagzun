# DjinnOS launch script
# Starts two proxies then boots QEMU:
#   :9000 -- Atelier proxy (HTTP->HTTPS to Render API)
#   :8080 -- Faerie Browser proxy (HTTP forward proxy for the kernel browser)
# If a port is already in use, that proxy step is skipped gracefully.

Set-Location $PSScriptRoot

$env:PATH += ";$env:USERPROFILE\.cargo\bin"

Write-Host "DjinnOS" -ForegroundColor Magenta

# --- Atelier proxy (:9000) ---------------------------------------------------
$atelierScript = Join-Path $PSScriptRoot "atelier_proxy.py"
$atelierProc   = $null

if (Test-Path $atelierScript) {
    Write-Host "Starting Atelier proxy on :9000..." -ForegroundColor Cyan
    $atelierProc = Start-Process python -ArgumentList $atelierScript `
                       -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 600

    if ($atelierProc.HasExited) {
        Write-Host "Atelier proxy exited immediately (port 9000 busy?)" -ForegroundColor Yellow
        $atelierProc = $null
    } else {
        Write-Host "Atelier proxy running (PID $($atelierProc.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "atelier_proxy.py not found -- skipping" -ForegroundColor Yellow
}

# --- Faerie Browser proxy (:8080) --------------------------------------------
$browserScript = Join-Path $PSScriptRoot "browser_proxy.py"
$browserProc   = $null

if (Test-Path $browserScript) {
    Write-Host "Starting Faerie Browser proxy on :8888..." -ForegroundColor Cyan
    $browserProc = Start-Process python -ArgumentList $browserScript `
                       -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 600

    if ($browserProc.HasExited) {
        Write-Host "Browser proxy exited immediately (port 8888 busy?)" -ForegroundColor Yellow
        $browserProc = $null
    } else {
        Write-Host "Faerie Browser proxy running (PID $($browserProc.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "browser_proxy.py not found -- skipping" -ForegroundColor Yellow
}

# --- Build and boot ----------------------------------------------------------
Write-Host "Building and booting..." -ForegroundColor Cyan
cargo run --release

if ($LASTEXITCODE -ne 0) {
    Write-Host "QEMU exited with code $LASTEXITCODE" -ForegroundColor Yellow
}

# --- Tear down proxies -------------------------------------------------------
if ($null -ne $atelierProc -and -not $atelierProc.HasExited) {
    $atelierProc.Kill()
    Write-Host "Atelier proxy stopped." -ForegroundColor DarkGray
}
if ($null -ne $browserProc -and -not $browserProc.HasExited) {
    $browserProc.Kill()
    Write-Host "Faerie Browser proxy stopped." -ForegroundColor DarkGray
}

Write-Host "DjinnOS session ended." -ForegroundColor DarkGray
Read-Host "Press Enter to close"