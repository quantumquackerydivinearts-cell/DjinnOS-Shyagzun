Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$apiRoot = "C:\DjinnOS\apps\atelier-api"
if (-not (Test-Path $apiRoot)) {
    throw "Atelier API path not found: $apiRoot"
}
$repoRoot = "C:\DjinnOS"
if (-not (Test-Path $repoRoot)) {
    throw "Repo root path not found: $repoRoot"
}

if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "sqlite:///C:/DjinnOS/apps/atelier-api/atelier_local.db"
}
if (-not $env:KERNEL_BASE_URL) {
    $env:KERNEL_BASE_URL = "http://127.0.0.1:8000"
}

# Ensure local packages (qqva at repo root + atelier_api package) are importable.
$env:PYTHONPATH = "$repoRoot;$apiRoot"

Set-Location $apiRoot
py -m uvicorn atelier_api.main:app --host 127.0.0.1 --port 9000
