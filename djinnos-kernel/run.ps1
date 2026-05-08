# DjinnOS launch script
# Starts the Atelier proxy (HTTP->HTTPS bridge on :9000) then boots QEMU.
# The proxy lets the kernel reach the hosted Render API without a local stack.
# If port 9000 is already in use the proxy step is skipped gracefully.

Set-Location $PSScriptRoot

$env:PATH += ";$env:USERPROFILE\.cargo\bin"

Write-Host "DjinnOS" -ForegroundColor Magenta

# --- Atelier proxy -----------------------------------------------------------
$proxyScript = Join-Path $PSScriptRoot "atelier_proxy.py"
$proxyProc   = $null

if (Test-Path $proxyScript) {
    Write-Host "Starting Atelier proxy on :9000..." -ForegroundColor Cyan
    $proxyProc = Start-Process python -ArgumentList $proxyScript `
                     -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 800

    if ($proxyProc.HasExited) {
        Write-Host "Proxy exited immediately (port 9000 busy? local API running?)" -ForegroundColor Yellow
        $proxyProc = $null
    } else {
        Write-Host "Atelier proxy running (PID $($proxyProc.Id))" -ForegroundColor Green
    }
} else {
    Write-Host "atelier_proxy.py not found -- skipping proxy" -ForegroundColor Yellow
}

# --- Build and boot ----------------------------------------------------------
Write-Host "Building and booting..." -ForegroundColor Cyan
cargo run --release

if ($LASTEXITCODE -ne 0) {
    Write-Host "QEMU exited with code $LASTEXITCODE" -ForegroundColor Yellow
}

# --- Tear down proxy ---------------------------------------------------------
if ($null -ne $proxyProc -and -not $proxyProc.HasExited) {
    $proxyProc.Kill()
    Write-Host "Atelier proxy stopped." -ForegroundColor DarkGray
}

Write-Host "DjinnOS session ended." -ForegroundColor DarkGray
Read-Host "Press Enter to close"