# DjinnOS — launch script
# Builds and boots DjinnOS in QEMU, with the Atelier proxy running alongside.
#
# The proxy forwards plain-HTTP :9000 to the hosted Render API over HTTPS,
# so the kernel reaches production without a local Atelier API process.
# If port 9000 is already occupied (local API running), the proxy skips itself.

Set-Location $PSScriptRoot

$env:PATH += ";$env:USERPROFILE\.cargo\bin"

Write-Host "DjinnOS" -ForegroundColor Magenta

# ── Start Atelier proxy ──────────────────────────────────────────────────────
$proxyScript = Join-Path $PSScriptRoot "atelier_proxy.py"
$proxyJob    = $null

if (Test-Path $proxyScript) {
    Write-Host "Starting Atelier proxy..." -ForegroundColor Cyan
    $proxyJob = Start-Job -ScriptBlock {
        param($script)
        python $script
    } -ArgumentList $proxyScript

    # Give it a moment to bind the port or fail.
    Start-Sleep -Milliseconds 600
    if ($proxyJob.State -eq "Failed") {
        Write-Host "Proxy failed to start (port 9000 busy? local API running?)" -ForegroundColor Yellow
        $proxyJob = $null
    } else {
        Write-Host "Atelier proxy live on :9000" -ForegroundColor Green
    }
} else {
    Write-Host "atelier_proxy.py not found — skipping proxy" -ForegroundColor Yellow
}

# ── Build and boot ───────────────────────────────────────────────────────────
Write-Host "Building and booting..." -ForegroundColor Cyan
cargo run --release

if ($LASTEXITCODE -ne 0) {
    Write-Host "QEMU exited with code $LASTEXITCODE" -ForegroundColor Yellow
}

# ── Tear down proxy ──────────────────────────────────────────────────────────
if ($null -ne $proxyJob) {
    Stop-Job  $proxyJob
    Remove-Job $proxyJob
    Write-Host "Atelier proxy stopped." -ForegroundColor DarkGray
}

Write-Host "DjinnOS session ended." -ForegroundColor DarkGray
Read-Host "Press Enter to close"