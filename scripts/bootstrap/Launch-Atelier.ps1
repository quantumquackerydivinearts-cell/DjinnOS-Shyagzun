param(
    [switch]$SkipDesktop
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms

function Show-LaunchError {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$LogPath = ""
    )

    $full = $Message
    if (-not [string]::IsNullOrWhiteSpace($LogPath)) {
        $full += "`n`nDetails: $LogPath"
    }
    [System.Windows.Forms.MessageBox]::Show(
        $full,
        "Ko's Labyrnth Atelier Launch Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
}

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSec = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Start-BackgroundPowerShell {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string]$StdOutLog,
        [Parameter(Mandatory = $true)]
        [string]$StdErrLog
    )

    $psExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    $wrapped = "Set-Location -LiteralPath '$WorkingDirectory'; $Command"
    return Start-Process -FilePath $psExe `
        -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $wrapped `
        -WindowStyle Hidden `
        -RedirectStandardOutput $StdOutLog `
        -RedirectStandardError $StdErrLog `
        -PassThru
}

function Resolve-PythonCommand {
    param([string]$Preferred = "")
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($Preferred)) { $candidates += $Preferred }
    $candidates += @("py", "python", "python3")
    foreach ($c in ($candidates | Select-Object -Unique)) {
        try {
            $null = Get-Command $c -ErrorAction Stop
            return $c
        } catch {
            continue
        }
    }
    return ""
}

function Install-RequirementsFromWheelhouse {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonCommand,
        [Parameter(Mandatory = $true)] [string]$RequirementsPath,
        [Parameter(Mandatory = $true)] [string]$WheelhouseDir
    )

    if (Test-Path -LiteralPath $WheelhouseDir) {
        & $PythonCommand -m pip install --no-index --find-links $WheelhouseDir -r $RequirementsPath
        if ($LASTEXITCODE -eq 0) {
            return
        }
    }

    # Controlled fallback if wheelhouse install fails or is unavailable.
    & $PythonCommand -m pip install -r $RequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency install failed for $RequirementsPath"
    }
}

function Ensure-PythonDependencies {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonCommand,
        [Parameter(Mandatory = $true)] [string]$ApiDir,
        [Parameter(Mandatory = $true)] [string]$KernelDir,
        [Parameter(Mandatory = $true)] [string]$WheelhouseDir,
        [Parameter(Mandatory = $true)] [string]$MarkerFile
    )

    if (Test-Path -LiteralPath $MarkerFile) {
        return
    }

    $apiReq = Join-Path $ApiDir "requirements.txt"
    if (Test-Path -LiteralPath $apiReq) {
        Install-RequirementsFromWheelhouse -PythonCommand $PythonCommand -RequirementsPath $apiReq -WheelhouseDir $WheelhouseDir
    }

    $kernelReq = Join-Path $KernelDir "requirements.txt"
    if (Test-Path -LiteralPath $kernelReq) {
        Install-RequirementsFromWheelhouse -PythonCommand $PythonCommand -RequirementsPath $kernelReq -WheelhouseDir $WheelhouseDir
    }

    New-Item -ItemType File -Path $MarkerFile -Force | Out-Null
}

try {
    $installRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $configPath = Join-Path $installRoot "config.json"
    if (-not (Test-Path -LiteralPath $configPath)) {
        throw "Missing config at $configPath"
    }
    $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json

    $metaDir = Join-Path $installRoot "meta"
    New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
    $launchLog = Join-Path $metaDir "launcher.log"
    ("[" + (Get-Date).ToString("s") + "] launch start") | Out-File -FilePath $launchLog -Append -Encoding utf8

    $desktopExePrimary = Join-Path $installRoot "desktop\Atelier Desktop.exe"
    $desktopExeFallback = Join-Path $installRoot "desktop\QuantumQuackeryAtelier.exe"
    $desktopExe = ""
    if (Test-Path -LiteralPath $desktopExePrimary) {
        $desktopExe = $desktopExePrimary
    } elseif (Test-Path -LiteralPath $desktopExeFallback) {
        $desktopExe = $desktopExeFallback
    } else {
        $candidate = Get-ChildItem -Path (Join-Path $installRoot "desktop") -Recurse -Filter "*.exe" |
            Where-Object { $_.Name -match "Atelier|QuantumQuackeryAtelier" } |
            Select-Object -First 1
        if ($candidate) { $desktopExe = $candidate.FullName }
    }
    if ([string]::IsNullOrWhiteSpace($desktopExe)) {
        throw "Desktop executable not found under $installRoot\desktop"
    }

    $backendMode = "local"
    $autoStart = $true
    $pythonCommand = "py"
    $kernelHost = "127.0.0.1"
    $kernelPort = 8000
    $apiHost = "127.0.0.1"
    $apiPort = 9000

    if ($config.backend) {
        if ($config.backend.mode) { $backendMode = [string]$config.backend.mode }
        if ($null -ne $config.backend.auto_start) { $autoStart = [bool]$config.backend.auto_start }
        if ($config.backend.python_command) { $pythonCommand = [string]$config.backend.python_command }
        if ($config.backend.kernel_host) { $kernelHost = [string]$config.backend.kernel_host }
        if ($config.backend.kernel_port) { $kernelPort = [int]$config.backend.kernel_port }
        if ($config.backend.api_host) { $apiHost = [string]$config.backend.api_host }
        if ($config.backend.api_port) { $apiPort = [int]$config.backend.api_port }
    }

    if ($backendMode -eq "local" -and $autoStart) {
        $pythonResolved = Resolve-PythonCommand -Preferred $pythonCommand
        if ([string]::IsNullOrWhiteSpace($pythonResolved)) {
            throw "Python runtime not found (tried: $pythonCommand, py, python, python3)."
        }
        $pythonCommand = $pythonResolved
        ("[" + (Get-Date).ToString("s") + "] python command: $pythonCommand") | Out-File -FilePath $launchLog -Append -Encoding utf8

        $apiBase = "http://${apiHost}:${apiPort}"
        $kernelBase = "http://${kernelHost}:${kernelPort}"
        $kernelEventsUrl = "${kernelBase}/events"
        $apiHealthUrl = "${apiBase}/health"

        $apiDir = Join-Path $installRoot "api"
        $kernelDir = Join-Path $installRoot "kernel"
        $wheelhouseDir = Join-Path $installRoot "wheelhouse"
        if (-not (Test-Path -LiteralPath (Join-Path $kernelDir "shygazun\kernel_service.py"))) {
            throw "Kernel bundle missing from install: $kernelDir"
        }
        if (-not (Test-Path -LiteralPath (Join-Path $apiDir "atelier_api\main.py"))) {
            throw "API bundle missing from install: $apiDir"
        }

        $depsMarker = Join-Path $metaDir "local_backend_ready.flag"
        Ensure-PythonDependencies -PythonCommand $pythonCommand -ApiDir $apiDir -KernelDir $kernelDir -WheelhouseDir $wheelhouseDir -MarkerFile $depsMarker

        if (-not (Test-HttpReady -Url $kernelEventsUrl -TimeoutSec 2)) {
            $kernelOut = Join-Path $metaDir "kernel.out.log"
            $kernelErr = Join-Path $metaDir "kernel.err.log"
            $kernelCmd = "$pythonCommand -m uvicorn shygazun.kernel_service:app --host $kernelHost --port $kernelPort --app-dir '$kernelDir'"
            $kernelProc = Start-BackgroundPowerShell -WorkingDirectory $kernelDir -Command $kernelCmd -StdOutLog $kernelOut -StdErrLog $kernelErr
            ("[" + (Get-Date).ToString("s") + "] kernel start pid: " + $kernelProc.Id) | Out-File -FilePath $launchLog -Append -Encoding utf8
        }
        if (-not (Test-HttpReady -Url $kernelEventsUrl -TimeoutSec 90)) {
            throw "Local kernel failed to start on $kernelBase"
        }

        if (-not (Test-HttpReady -Url $apiHealthUrl -TimeoutSec 2)) {
            $apiOut = Join-Path $metaDir "api.out.log"
            $apiErr = Join-Path $metaDir "api.err.log"
            $sqlitePath = (Join-Path $apiDir "atelier_local.db") -replace "\\", "/"
            $apiCmd = "`$env:DATABASE_URL='sqlite:///$sqlitePath'; `$env:KERNEL_BASE_URL='$kernelBase'; `$env:PYTHONPATH='$installRoot;$apiDir'; $pythonCommand -m uvicorn atelier_api.main:app --host $apiHost --port $apiPort --app-dir '$apiDir'"
            $apiProc = Start-BackgroundPowerShell -WorkingDirectory $apiDir -Command $apiCmd -StdOutLog $apiOut -StdErrLog $apiErr
            ("[" + (Get-Date).ToString("s") + "] api start pid: " + $apiProc.Id) | Out-File -FilePath $launchLog -Append -Encoding utf8
        }
        if (-not (Test-HttpReady -Url $apiHealthUrl -TimeoutSec 90)) {
            throw "Local API failed to start on $apiBase"
        }
    }

    if (-not $SkipDesktop) {
        Start-Process -FilePath $desktopExe | Out-Null
    }
} catch {
    $installRoot = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $env:TEMP }
    $metaDir = Join-Path $installRoot "meta"
    New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
    $launchLog = Join-Path $metaDir "launcher.log"
    ("[" + (Get-Date).ToString("s") + "] error: " + $_.Exception.Message) | Out-File -FilePath $launchLog -Append -Encoding utf8
    Show-LaunchError -Message $_.Exception.Message -LogPath $launchLog
    exit 1
}
