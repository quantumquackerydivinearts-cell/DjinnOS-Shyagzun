Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

try {
    $apiRoot = "C:\DjinnOS\apps\atelier-api"
    if (-not (Test-Path $apiRoot)) {
        throw "Atelier API path not found: $apiRoot"
    }
    $repoRoot = "C:\DjinnOS"
    if (-not (Test-Path $repoRoot)) {
        throw "Repo root path not found: $repoRoot"
    }

    [System.Environment]::SetEnvironmentVariable("PYTHONPATH", "$repoRoot;$apiRoot", "Process")
    [System.Environment]::SetEnvironmentVariable("DATABASE_URL", "sqlite:///C:/DjinnOS/apps/atelier-api/atelier_local.db", "Process")
    [System.Environment]::SetEnvironmentVariable("KERNEL_BASE_URL", "http://127.0.0.1:8000", "Process")

    Set-Location $apiRoot
    python -m uvicorn atelier_api.main:app --host 127.0.0.1 --port 9000 2>&1 | Tee-Object -FilePath "C:\DjinnOS\api.log"

} catch {
    $_ | Out-File "C:\DjinnOS\api-error.log"
    Write-Host "ERROR: $_"
    Read-Host "Press Enter to close"
}