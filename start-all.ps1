param(
    [switch]$VerifyShygazun,
    [ValidateSet("dev", "desktop")]
    [string]$UiMode = "dev"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$stackScript = "C:\DjinnOS\scripts\start_atelier_stack.ps1"
if (-not (Test-Path -LiteralPath $stackScript)) {
    throw "Stack launcher not found: $stackScript"
}

# Starts:
# 1) Kernel service (uvicorn 127.0.0.1:8000)
# 2) Atelier API service (uvicorn 127.0.0.1:9000)
# 3) Desktop shell (UiMode=dev => Vite + Electron main)
& $stackScript -UiMode $UiMode

if ($VerifyShygazun) {
    Start-Sleep -Seconds 2
    & "C:\DjinnOS\scripts\verify_shygazun_surfaces.ps1"
}
