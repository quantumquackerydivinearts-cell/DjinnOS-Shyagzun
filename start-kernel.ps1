Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = "C:\DjinnOS\DjinnOS-Shyagzun"
if (-not (Test-Path $repoRoot)) {
    throw "Kernel repo path not found: $repoRoot"
}

Set-Location $repoRoot
python -m uvicorn shygazun.kernel_service:app --host 127.0.0.1 --port 8000 --reload
