param(
    [string]$Version = "",
    [ValidateSet("local", "hosted")]
    [string]$Target = "local",
    [switch]$SkipGoNoGo,
    [switch]$SkipRebuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-PythonCommand {
    $candidates = @("py", "python", "python3")
    foreach ($candidate in $candidates) {
        try {
            $null = Get-Command $candidate -ErrorAction Stop
            & $candidate --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
        try {
            & $candidate -V *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
    }
    throw "Python runtime not found (tried: py, python, python3)."
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = (Get-Date -Format "yyyyMMdd-HHmmss")
}

$repoRoot = "C:\DjinnOS"
$releaseRoot = Join-Path $repoRoot "releases\$Version"
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

$targetName = if ($Target -eq "local") { "Local Atelier Bundle" } else { "Hosted Atelier Stack" }
$bundlePrefix = if ($Target -eq "local") { "atelier-suite" } else { "atelier-hosted-suite" }
$pythonCommand = ""

$goNoGoScript = Join-Path $repoRoot "scripts\production_go_no_go.py"
$goNoGoMetrics = Join-Path $repoRoot "reports\production_go_no_go.metrics.json"
$desktopAppRoot = Join-Path $repoRoot "apps\atelier-desktop"
$desktopPackedDir = Join-Path $desktopAppRoot "release\desktop\win-unpacked"
$desktopZip = Join-Path $repoRoot "apps\atelier-desktop\release\QuantumQuackeryAtelier-win32-x64.zip"
$apiAppRoot = Join-Path $repoRoot "apps\atelier-api"
$apiZip = Join-Path $repoRoot "apps\atelier-api\release\atelier-api-bundle.zip"

function New-ApiBundleZip {
    param(
        [string]$ApiRoot,
        [string]$OutZip
    )

    $staging = Join-Path ([System.IO.Path]::GetTempPath()) ("atelier-api-bundle-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    try {
        Copy-Item -Recurse -Force (Join-Path $ApiRoot "alembic") (Join-Path $staging "alembic")
        Copy-Item -Recurse -Force (Join-Path $ApiRoot "atelier_api") (Join-Path $staging "atelier_api")
        Copy-Item -Force (Join-Path $ApiRoot "alembic.ini") (Join-Path $staging "alembic.ini")
        Copy-Item -Force (Join-Path $ApiRoot "requirements.txt") (Join-Path $staging "requirements.txt")
        if (Test-Path $OutZip) { Remove-Item -Force $OutZip }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($staging, $OutZip)
    } finally {
        if (Test-Path $staging) {
            Remove-Item -Recurse -Force $staging
        }
    }
}

if (-not $SkipRebuild) {
    Write-Host "Rebuilding desktop release directory..."
    Push-Location $desktopAppRoot
    try {
        npm.cmd run pack:desktop:dir
        if ($LASTEXITCODE -ne 0) {
            throw "Desktop directory pack failed."
        }
    } finally {
        Pop-Location
    }

    if (-not (Test-Path $desktopPackedDir)) {
        throw "Desktop packed directory not found at $desktopPackedDir"
    }

    Write-Host "Refreshing desktop zip artifact..."
    if (Test-Path $desktopZip) {
        Remove-Item -Force $desktopZip
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($desktopPackedDir, $desktopZip)

    Write-Host "Refreshing API bundle zip..."
    New-ApiBundleZip -ApiRoot $apiAppRoot -OutZip $apiZip
}

if (-not $SkipGoNoGo) {
    if ([string]::IsNullOrWhiteSpace($pythonCommand)) {
        $pythonCommand = Resolve-PythonCommand
    }
    if (-not (Test-Path $goNoGoScript)) {
        throw "Go/No-Go script not found at $goNoGoScript"
    }
    Write-Host "Running production go/no-go gate..."
    & $pythonCommand $goNoGoScript --skip-build
    if ($LASTEXITCODE -ne 0) {
        throw "Production go/no-go gate failed. Packaging aborted."
    }
    if (-not (Test-Path $goNoGoMetrics)) {
        throw "Go/No-Go metrics not found at $goNoGoMetrics"
    }
}
$kernelRepo = Join-Path $repoRoot "DjinnOS_Shyagzun"
$kernelSourceDir = Join-Path $kernelRepo "shygazun"
$kernelBundleZip = Join-Path $releaseRoot "kernel-runtime-bundle.zip"
$wheelhouseZip = Join-Path $releaseRoot "python-wheelhouse.zip"
$androidRoot = Join-Path $repoRoot "apps\atelier-desktop\release\android"
$startupScript = Join-Path $repoRoot "scripts\start_atelier_stack.ps1"
$apiRequirements = Join-Path $repoRoot "apps\atelier-api\requirements.txt"
$hostedDeploymentDir = Join-Path $repoRoot "deployment\hosted"

if (-not (Test-Path $desktopZip)) {
    throw "Desktop zip not found at $desktopZip"
}
if (-not (Test-Path $apiZip)) {
    throw "API zip not found at $apiZip"
}
if (-not (Test-Path $kernelSourceDir)) {
    throw "Kernel source directory not found at $kernelSourceDir"
}
if (-not (Test-Path $apiRequirements)) {
    throw "API requirements not found at $apiRequirements"
}
if ($Target -eq "local" -and -not (Test-Path $startupScript)) {
    throw "Startup script not found at $startupScript"
}
if ($Target -eq "hosted" -and -not (Test-Path $hostedDeploymentDir)) {
    throw "Hosted deployment assets not found at $hostedDeploymentDir"
}

$latestAndroid = Get-ChildItem -Directory $androidRoot -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latestAndroid) {
    throw "No Android release directory found in $androidRoot"
}

Copy-Item -Force $desktopZip (Join-Path $releaseRoot "atelier-desktop-win32-x64.zip")
Copy-Item -Force $apiZip (Join-Path $releaseRoot "atelier-api-bundle.zip")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-release.apk") (Join-Path $releaseRoot "atelier-android-release.apk")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-release.aab") (Join-Path $releaseRoot "atelier-android-release.aab")
Copy-Item -Force (Join-Path $latestAndroid.FullName "app-debug.apk") (Join-Path $releaseRoot "atelier-android-debug.apk")

$manifestArtifacts = @(
    "atelier-desktop-win32-x64.zip",
    "atelier-api-bundle.zip",
    "atelier-android-release.apk",
    "atelier-android-release.aab",
    "atelier-android-debug.apk"
)

if ($Target -eq "local") {
    if ([string]::IsNullOrWhiteSpace($pythonCommand)) {
        $pythonCommand = Resolve-PythonCommand
    }
    $kernelStage = Join-Path $env:TEMP ("kernel-bundle-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $kernelStage | Out-Null
    try {
        $kernelStageRoot = Join-Path $kernelStage "kernel-runtime"
        New-Item -ItemType Directory -Force -Path $kernelStageRoot | Out-Null
        Copy-Item -Recurse -Force $kernelSourceDir (Join-Path $kernelStageRoot "shygazun")
        @(
            "fastapi",
            "uvicorn",
            "pydantic"
        ) | Out-File -FilePath (Join-Path $kernelStageRoot "requirements.txt") -Encoding ascii
        "Local kernel runtime bundle for Ko's Labyrnth Atelier." |
            Out-File -FilePath (Join-Path $kernelStageRoot "README.txt") -Encoding ascii
        Compress-Archive -Path (Join-Path $kernelStageRoot "*") -DestinationPath $kernelBundleZip -CompressionLevel Optimal
    } finally {
        if (Test-Path $kernelStage) {
            Remove-Item -Recurse -Force $kernelStage
        }
    }

    $wheelhouseStage = Join-Path $env:TEMP ("wheelhouse-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $wheelhouseStage | Out-Null
    try {
        $wheelhouseDir = Join-Path $wheelhouseStage "wheelhouse"
        New-Item -ItemType Directory -Force -Path $wheelhouseDir | Out-Null

        $combinedReq = Join-Path $wheelhouseStage "requirements-combined.txt"
        $apiLines = Get-Content $apiRequirements |
            Where-Object { $_ -and ($_ -notmatch "^\s*#") } |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and ($_ -notmatch "^psycopg(\[.*\])?$") -and ($_ -notmatch "^alembic$") }
        $kernelLines = @(
            "fastapi",
            "uvicorn",
            "requests",
            "sqlalchemy",
            "pydantic"
        )
        $combined = ($apiLines + $kernelLines | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)
        $combined | Out-File -FilePath $combinedReq -Encoding ascii

        & $pythonCommand -m pip wheel --wheel-dir $wheelhouseDir -r $combinedReq
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to build python wheelhouse"
        }

        Compress-Archive -Path (Join-Path $wheelhouseDir "*") -DestinationPath $wheelhouseZip -CompressionLevel Optimal
    } finally {
        if (Test-Path $wheelhouseStage) {
            Remove-Item -Recurse -Force $wheelhouseStage
        }
    }

    Copy-Item -Force $startupScript (Join-Path $releaseRoot "start_atelier_stack.ps1")
    $manifestArtifacts += @(
        "kernel-runtime-bundle.zip",
        "python-wheelhouse.zip",
        "start_atelier_stack.ps1"
    )
} else {
    $hostedNotesPath = Join-Path $releaseRoot "HOSTED-SETUP.txt"
    @(
        "Hosted Atelier Stack",
        "",
        "This package is intended for managed deployments.",
        "Use PostgreSQL for DATABASE_URL.",
        "Run Alembic migrations before exposing the API.",
        "Provide kernel and API as managed services rather than local desktop-spawned processes.",
        "",
        "Required environment:",
        "- DATABASE_URL=postgresql+psycopg://...",
        "- KERNEL_BASE_URL=http://<host>:<port>",
        "- AUTH_TOKEN_SECRET=<real-secret>"
    ) | Out-File -FilePath $hostedNotesPath -Encoding ascii
    Copy-Item -Recurse -Force $hostedDeploymentDir (Join-Path $releaseRoot "hosted-deployment")
    $manifestArtifacts += @(
        "HOSTED-SETUP.txt",
        "hosted-deployment"
    )
}

if ((-not $SkipGoNoGo) -and (Test-Path $goNoGoMetrics)) {
    Copy-Item -Force $goNoGoMetrics (Join-Path $releaseRoot "production_go_no_go.metrics.json")
}
if (-not $SkipGoNoGo) {
    $manifestArtifacts += "production_go_no_go.metrics.json"
}

$manifest = [ordered]@{
    version = $Version
    target = $Target
    target_name = $targetName
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    artifacts = $manifestArtifacts
    backend = if ($Target -eq "local") {
        [ordered]@{
            mode = "embedded"
            database = "sqlite"
            kernel_delivery = "bundled"
            dependency_bootstrap = "offline wheelhouse"
        }
    } else {
        [ordered]@{
            mode = "managed"
            database = "postgres"
            kernel_delivery = "external service"
            dependency_bootstrap = "deployment-managed"
        }
    }
    quality_gate = [ordered]@{
        go_no_go_enforced = (-not $SkipGoNoGo)
        metrics_file = if (-not $SkipGoNoGo) { "production_go_no_go.metrics.json" } else { "" }
    }
}

$manifestPath = Join-Path $releaseRoot "manifest.json"
$manifest | ConvertTo-Json -Depth 5 | Out-File -FilePath $manifestPath -Encoding UTF8

$bundleZip = Join-Path (Split-Path $releaseRoot -Parent) ($bundlePrefix + "-" + $Version + ".zip")
if (Test-Path $bundleZip) {
    Remove-Item -Force $bundleZip
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($releaseRoot, $bundleZip)

Get-ChildItem -File $releaseRoot | Select-Object Name,Length,LastWriteTime
Write-Host "Suite bundle created: $bundleZip"
