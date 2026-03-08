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
        [int]$TimeoutSec = 90,
        [int]$SuccessStatusMin = 200,
        [int]$SuccessStatusMax = 299
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -ge $SuccessStatusMin -and $resp.StatusCode -le $SuccessStatusMax) {
                return $true
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    return $false
}

function Test-KernelReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,
        [int]$TimeoutSec = 5
    )

    $root = $BaseUrl.TrimEnd("/")
    $eventsUrl = ($root + "/events")
    $fieldUrl = ($root + "/v0.1/field/F0")
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $eventsUrl -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -lt 200 -or $resp.StatusCode -gt 299) {
                Start-Sleep -Milliseconds 500
                continue
            }
            $payload = $resp.Content | ConvertFrom-Json
            if (-not ($payload -is [System.Array])) {
                Start-Sleep -Milliseconds 500
                continue
            }
            $fieldResp = Invoke-WebRequest -Uri $fieldUrl -UseBasicParsing -TimeoutSec 2
            if ($fieldResp.StatusCode -lt 200 -or $fieldResp.StatusCode -gt 299) {
                Start-Sleep -Milliseconds 500
                continue
            }
            $fieldPayload = $fieldResp.Content | ConvertFrom-Json
            if (($fieldPayload -is [pscustomobject]) -and ($null -ne $fieldPayload.field)) {
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

function Test-PortAvailable {
    param(
        [Parameter(Mandatory = $true)] [string]$Host,
        [Parameter(Mandatory = $true)] [int]$Port
    )

    $listener = $null
    try {
        $ip = [System.Net.IPAddress]::Parse($Host)
        $listener = [System.Net.Sockets.TcpListener]::new($ip, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            try { $listener.Stop() } catch { }
        }
    }
}

function Test-ManagedProcessId {
    param(
        [Parameter(Mandatory = $true)] [int]$ProcessId,
        [Parameter(Mandatory = $true)] [string]$InstallRoot
    )

    try {
        $proc = Get-CimInstance Win32_Process -Filter ("ProcessId = " + $ProcessId) -ErrorAction Stop
    } catch {
        return $false
    }

    $commandLine = ""
    $executablePath = ""
    try { $commandLine = [string]$proc.CommandLine } catch { }
    try { $executablePath = [string]$proc.ExecutablePath } catch { }

    if (-not [string]::IsNullOrWhiteSpace($commandLine) -and $commandLine.IndexOf($InstallRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
        return $true
    }
    if (-not [string]::IsNullOrWhiteSpace($executablePath) -and $executablePath.IndexOf($InstallRoot, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) {
        return $true
    }
    if (-not [string]::IsNullOrWhiteSpace($commandLine)) {
        if (
            $commandLine.IndexOf("atelier_api.main:app", [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $commandLine.IndexOf("kernel_service:app", [System.StringComparison]::OrdinalIgnoreCase) -ge 0 -or
            $commandLine.IndexOf("shygazun.kernel_service:app", [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        ) {
            return $true
        }
    }

    return $false
}

function Stop-ListenersOnPort {
    param(
        [Parameter(Mandatory = $true)] [string]$InstallRoot,
        [Parameter(Mandatory = $true)] [int]$Port,
        [Parameter(Mandatory = $true)] [string]$LogPath
    )

    $pids = @()
    try {
        $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        foreach ($c in $conns) {
            if ($null -ne $c.OwningProcess) { $pids += [int]$c.OwningProcess }
        }
    } catch {
        $lines = netstat -ano -p tcp | Select-String -Pattern (":$Port\s")
        foreach ($line in $lines) {
            $txt = ($line.ToString().Trim() -replace "\s+", " ")
            $parts = $txt.Split(" ")
            if ($parts.Length -ge 5) {
                $pidText = $parts[$parts.Length - 1]
                $pidValue = 0
                if ([int]::TryParse($pidText, [ref]$pidValue)) {
                    $pids += $pidValue
                }
            }
        }
    }

    foreach ($procId in ($pids | Select-Object -Unique)) {
        if ($procId -le 0) { continue }
        if (-not (Test-ManagedProcessId -ProcessId $procId -InstallRoot $InstallRoot)) {
            ("[" + (Get-Date).ToString("s") + "] leaving unrelated listener pid " + $procId + " on port " + $Port) | Out-File -FilePath $LogPath -Append -Encoding utf8
            continue
        }
        try {
            Stop-Process -Id $procId -Force -ErrorAction Stop
            ("[" + (Get-Date).ToString("s") + "] killed listener pid " + $procId + " on port " + $Port) | Out-File -FilePath $LogPath -Append -Encoding utf8
        } catch {
            ("[" + (Get-Date).ToString("s") + "] failed to kill pid " + $procId + " on port " + $Port + ": " + $_.Exception.Message) | Out-File -FilePath $LogPath -Append -Encoding utf8
        }
    }
}

function Resolve-PythonCommand {
    param([string]$Preferred = "")
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($Preferred)) { $candidates += $Preferred }
    $candidates += @("py", "python", "python3")
    foreach ($c in ($candidates | Select-Object -Unique)) {
        try {
            $null = Get-Command $c -ErrorAction Stop
            & $c --version *> $null
            if ($LASTEXITCODE -eq 0) {
                return $c
            }
        } catch {
        }
        try {
            & $c -V *> $null
            if ($LASTEXITCODE -eq 0) {
                return $c
            }
        } catch {
        }
    }
    return ""
}

function Ensure-PipAvailable {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonCommand
    )

    & $PythonCommand -m pip --version *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    & $PythonCommand -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Python runtime is missing pip and ensurepip bootstrap failed."
    }
}

function Resolve-ManagedPythonCommand {
    param(
        [Parameter(Mandatory = $true)] [string]$BasePythonCommand,
        [Parameter(Mandatory = $true)] [string]$InstallRoot
    )

    $venvDir = Join-Path $InstallRoot "python-runtime"
    $venvPython = Join-Path $venvDir "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        & $BasePythonCommand -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            return $BasePythonCommand
        }
    }
    if (Test-Path -LiteralPath $venvPython) {
        return $venvPython
    }
    return $BasePythonCommand
}

function New-LocalRuntimeRequirements {
    param(
        [Parameter(Mandatory = $true)] [string]$MetaDir
    )

    $reqPath = Join-Path $MetaDir "local-runtime-requirements.txt"
    @(
        "fastapi",
        "uvicorn",
        "requests",
        "sqlalchemy",
        "pydantic"
    ) | Out-File -LiteralPath $reqPath -Encoding ascii
    return $reqPath
}

function Install-RequirementsFromWheelhouse {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonCommand,
        [Parameter(Mandatory = $true)] [string]$RequirementsPath,
        [Parameter(Mandatory = $true)] [string]$WheelhouseDir
    )

    if (-not (Test-Path -LiteralPath $WheelhouseDir)) {
        throw "Bundled wheelhouse not found at $WheelhouseDir"
    }

    & $PythonCommand -m pip install --no-index --find-links $WheelhouseDir -r $RequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Offline dependency install failed for $RequirementsPath using wheelhouse $WheelhouseDir"
    }
}

function Ensure-PythonDependencies {
    param(
        [Parameter(Mandatory = $true)] [string]$PythonCommand,
        [Parameter(Mandatory = $true)] [string]$WheelhouseDir,
        [Parameter(Mandatory = $true)] [string]$MetaDir,
        [Parameter(Mandatory = $true)] [string]$MarkerFile
    )

    if (Test-Path -LiteralPath $MarkerFile) {
        return
    }

    Ensure-PipAvailable -PythonCommand $PythonCommand
    $runtimeReq = New-LocalRuntimeRequirements -MetaDir $MetaDir
    Install-RequirementsFromWheelhouse -PythonCommand $PythonCommand -RequirementsPath $runtimeReq -WheelhouseDir $WheelhouseDir

    New-Item -ItemType File -Path $MarkerFile -Force | Out-Null
}

function Get-LogTail {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [int]$Lines = 20
    )
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    try {
        return (Get-Content -LiteralPath $Path -Tail $Lines -ErrorAction Stop) -join "`n"
    } catch {
        return ""
    }
}

$launcherMutex = $null
try {
    $launcherMutex = New-Object System.Threading.Mutex($false, "Global\KosLabyrnth.Atelier.Launch")
    if (-not $launcherMutex.WaitOne(0, $false)) {
        exit 0
    }

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
    $pythonCommand = "python"
    $kernelHost = "127.0.0.1"
    $kernelPort = 8000
    $apiHost = "127.0.0.1"
    $apiPort = 9000
    $apiBase = "http://${apiHost}:${apiPort}"
    $kernelBase = "http://${kernelHost}:${kernelPort}"

    if ($config.backend) {
        if ($config.backend.mode) { $backendMode = [string]$config.backend.mode }
        if ($null -ne $config.backend.auto_start) { $autoStart = [bool]$config.backend.auto_start }
        if ($config.backend.python_command) { $pythonCommand = [string]$config.backend.python_command }
        if ($config.backend.kernel_host) { $kernelHost = [string]$config.backend.kernel_host }
        if ($config.backend.kernel_port) { $kernelPort = [int]$config.backend.kernel_port }
        if ($config.backend.api_host) { $apiHost = [string]$config.backend.api_host }
        if ($config.backend.api_port) { $apiPort = [int]$config.backend.api_port }
    }
    if ($config.api_base_url) { $apiBase = [string]$config.api_base_url }
    else { $apiBase = "http://${apiHost}:${apiPort}" }
    if ($config.kernel_base_url) { $kernelBase = [string]$config.kernel_base_url }
    else { $kernelBase = "http://${kernelHost}:${kernelPort}" }

    if ($backendMode -eq "local" -and $autoStart) {
        $pythonResolved = Resolve-PythonCommand -Preferred $pythonCommand
        if ([string]::IsNullOrWhiteSpace($pythonResolved)) {
            throw "Python runtime not found (tried: $pythonCommand, py, python, python3)."
        }
        $pythonCommand = Resolve-ManagedPythonCommand -BasePythonCommand $pythonResolved -InstallRoot $installRoot
        ("[" + (Get-Date).ToString("s") + "] python command: $pythonCommand") | Out-File -FilePath $launchLog -Append -Encoding utf8

        $apiBase = "http://${apiHost}:${apiPort}"
        $kernelBase = "http://${kernelHost}:${kernelPort}"
        $kernelEventsUrl = "${kernelBase}/events"
        $apiHealthUrl = "${apiBase}/health"
        ("[" + (Get-Date).ToString("s") + "] configured kernel base: " + $kernelBase) | Out-File -FilePath $launchLog -Append -Encoding utf8
        ("[" + (Get-Date).ToString("s") + "] configured api base: " + $apiBase) | Out-File -FilePath $launchLog -Append -Encoding utf8

        $kernelAlreadyReady = Test-KernelReady -BaseUrl $kernelBase -TimeoutSec 2
        $apiAlreadyReady = Test-HttpReady -Url $apiHealthUrl -TimeoutSec 2
        if ($kernelAlreadyReady -and $apiAlreadyReady) {
            ("[" + (Get-Date).ToString("s") + "] backend already healthy, skipping restart") | Out-File -FilePath $launchLog -Append -Encoding utf8
        } else {
            # Reclaim target ports only when backend is unhealthy to avoid self-thrashing on repeated launches.
            Stop-ListenersOnPort -InstallRoot $installRoot -Port $kernelPort -LogPath $launchLog
            Stop-ListenersOnPort -InstallRoot $installRoot -Port $apiPort -LogPath $launchLog
            Start-Sleep -Milliseconds 500
        }

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
        Ensure-PythonDependencies -PythonCommand $pythonCommand -WheelhouseDir $wheelhouseDir -MetaDir $metaDir -MarkerFile $depsMarker

        if (-not (Test-KernelReady -BaseUrl $kernelBase -TimeoutSec 2)) {
            $kernelStarted = $false
            $kernelAttempts = @(
                @{ appDir = $kernelDir; module = "shygazun.kernel_service:app" },
                @{ appDir = (Join-Path $kernelDir "shygazun"); module = "kernel_service:app" }
            )
            $kernelPorts = @($kernelPort, ($kernelPort + 1), ($kernelPort + 2), ($kernelPort + 10), ($kernelPort + 20)) | Select-Object -Unique
            $attemptIndex = 0
            foreach ($attempt in $kernelAttempts) {
                if (-not (Test-Path -LiteralPath $attempt.appDir)) { continue }
                foreach ($candidatePort in $kernelPorts) {
                    $attemptIndex++
                    $kernelBaseCandidate = "http://${kernelHost}:${candidatePort}"
                    $kernelEventsCandidate = "${kernelBaseCandidate}/events"
                    if (Test-KernelReady -BaseUrl $kernelBaseCandidate -TimeoutSec 2) {
                        $kernelPort = [int]$candidatePort
                        $kernelBase = $kernelBaseCandidate
                        $kernelEventsUrl = $kernelEventsCandidate
                        $kernelStarted = $true
                        ("[" + (Get-Date).ToString("s") + "] kernel already healthy on " + $kernelBaseCandidate) | Out-File -FilePath $launchLog -Append -Encoding utf8
                        break
                    }
                    if (-not (Test-PortAvailable -Host $kernelHost -Port $candidatePort)) {
                        ("[" + (Get-Date).ToString("s") + "] kernel candidate port busy: " + $candidatePort) | Out-File -FilePath $launchLog -Append -Encoding utf8
                        continue
                    }

                    $kernelOut = Join-Path $metaDir ("kernel.out." + $attemptIndex + ".log")
                    $kernelErr = Join-Path $metaDir ("kernel.err." + $attemptIndex + ".log")
                    $kernelCmd = "`$env:PYTHONPATH='$installRoot;$kernelDir;' + (`$env:PYTHONPATH); $pythonCommand -m uvicorn $($attempt.module) --host $kernelHost --port $candidatePort --app-dir '$($attempt.appDir)'"
                    $kernelProc = Start-BackgroundPowerShell -WorkingDirectory $attempt.appDir -Command $kernelCmd -StdOutLog $kernelOut -StdErrLog $kernelErr
                    ("[" + (Get-Date).ToString("s") + "] kernel attempt " + $attemptIndex + " pid: " + $kernelProc.Id + " module=" + $attempt.module + " appDir=" + $attempt.appDir + " port=" + $candidatePort) | Out-File -FilePath $launchLog -Append -Encoding utf8

                    if (Test-KernelReady -BaseUrl $kernelBaseCandidate -TimeoutSec 20) {
                        $kernelPort = [int]$candidatePort
                        $kernelBase = $kernelBaseCandidate
                        $kernelEventsUrl = $kernelEventsCandidate
                        $kernelStarted = $true
                        ("[" + (Get-Date).ToString("s") + "] kernel healthy after start attempt on " + $kernelBaseCandidate) | Out-File -FilePath $launchLog -Append -Encoding utf8
                        break
                    }

                    $errTail = Get-LogTail -Path $kernelErr -Lines 12
                    if (-not [string]::IsNullOrWhiteSpace($errTail)) {
                        ("[" + (Get-Date).ToString("s") + "] kernel attempt " + $attemptIndex + " stderr:`n" + $errTail) | Out-File -FilePath $launchLog -Append -Encoding utf8
                    }
                }
                if ($kernelStarted) { break }
            }
            if (-not $kernelStarted) {
                throw "Local kernel failed to start. See logs in $metaDir (kernel.err.*.log)."
            }
        }
        if (-not (Test-KernelReady -BaseUrl $kernelBase -TimeoutSec 30)) {
            throw "Local kernel failed to become healthy on $kernelBase"
        }
        ("[" + (Get-Date).ToString("s") + "] kernel ready: " + $kernelBase) | Out-File -FilePath $launchLog -Append -Encoding utf8

        if (-not (Test-HttpReady -Url $apiHealthUrl -TimeoutSec 2)) {
            $apiStarted = $false
            $apiPorts = @($apiPort, ($apiPort + 1), ($apiPort + 2), ($apiPort + 10), ($apiPort + 20)) | Select-Object -Unique
            $apiAttemptIndex = 0
            foreach ($candidateApiPort in $apiPorts) {
                $apiAttemptIndex++
                $apiBaseCandidate = "http://${apiHost}:${candidateApiPort}"
                $apiHealthCandidate = "${apiBaseCandidate}/health"
                if (Test-HttpReady -Url $apiHealthCandidate -TimeoutSec 2) {
                    $apiPort = [int]$candidateApiPort
                    $apiBase = $apiBaseCandidate
                    $apiHealthUrl = $apiHealthCandidate
                    $apiStarted = $true
                    ("[" + (Get-Date).ToString("s") + "] api already healthy on " + $apiBaseCandidate) | Out-File -FilePath $launchLog -Append -Encoding utf8
                    break
                }
                if (-not (Test-PortAvailable -Host $apiHost -Port $candidateApiPort)) {
                    ("[" + (Get-Date).ToString("s") + "] api candidate port busy: " + $candidateApiPort) | Out-File -FilePath $launchLog -Append -Encoding utf8
                    continue
                }

                $apiOut = Join-Path $metaDir ("api.out." + $apiAttemptIndex + ".log")
                $apiErr = Join-Path $metaDir ("api.err." + $apiAttemptIndex + ".log")
                $sqlitePath = (Join-Path $apiDir "atelier_local.db") -replace "\\", "/"
                $apiCmd = "`$env:DATABASE_URL='sqlite:///$sqlitePath'; `$env:KERNEL_BASE_URL='$kernelBase'; `$env:PYTHONPATH='$installRoot;$apiDir'; $pythonCommand -m uvicorn atelier_api.main:app --host $apiHost --port $candidateApiPort --app-dir '$apiDir'"
                $apiProc = Start-BackgroundPowerShell -WorkingDirectory $apiDir -Command $apiCmd -StdOutLog $apiOut -StdErrLog $apiErr
                ("[" + (Get-Date).ToString("s") + "] api attempt " + $apiAttemptIndex + " pid: " + $apiProc.Id + " port=" + $candidateApiPort) | Out-File -FilePath $launchLog -Append -Encoding utf8

                if (Test-HttpReady -Url $apiHealthCandidate -TimeoutSec 30) {
                    $apiPort = [int]$candidateApiPort
                    $apiBase = $apiBaseCandidate
                    $apiHealthUrl = $apiHealthCandidate
                    $apiStarted = $true
                    ("[" + (Get-Date).ToString("s") + "] api healthy after start attempt on " + $apiBaseCandidate) | Out-File -FilePath $launchLog -Append -Encoding utf8
                    break
                }

                $apiErrTail = Get-LogTail -Path $apiErr -Lines 12
                if (-not [string]::IsNullOrWhiteSpace($apiErrTail)) {
                    ("[" + (Get-Date).ToString("s") + "] api attempt " + $apiAttemptIndex + " stderr:`n" + $apiErrTail) | Out-File -FilePath $launchLog -Append -Encoding utf8
                }
            }
            if (-not $apiStarted) {
                throw "Local API failed to start. See logs in $metaDir (api.err.*.log)."
            }
        }
        if (-not (Test-HttpReady -Url $apiHealthUrl -TimeoutSec 30)) {
            throw "Local API failed to become healthy on $apiBase"
        }
        ("[" + (Get-Date).ToString("s") + "] api ready: " + $apiBase) | Out-File -FilePath $launchLog -Append -Encoding utf8
    } else {
        ("[" + (Get-Date).ToString("s") + "] remote mode: " + $backendMode) | Out-File -FilePath $launchLog -Append -Encoding utf8
        ("[" + (Get-Date).ToString("s") + "] configured kernel base: " + $kernelBase) | Out-File -FilePath $launchLog -Append -Encoding utf8
        ("[" + (Get-Date).ToString("s") + "] configured api base: " + $apiBase) | Out-File -FilePath $launchLog -Append -Encoding utf8
    }

    if (-not $SkipDesktop) {
        $env:KOS_API_BASE = $apiBase
        $env:KOS_KERNEL_BASE = $kernelBase
        Start-Process -FilePath $desktopExe -WorkingDirectory (Split-Path -Parent $desktopExe) | Out-Null
    }
} catch {
    $installRoot = if ($MyInvocation.MyCommand.Path) { Split-Path -Parent $MyInvocation.MyCommand.Path } else { $env:TEMP }
    $metaDir = Join-Path $installRoot "meta"
    New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
    $launchLog = Join-Path $metaDir "launcher.log"
    ("[" + (Get-Date).ToString("s") + "] error: " + $_.Exception.Message) | Out-File -FilePath $launchLog -Append -Encoding utf8
    Show-LaunchError -Message $_.Exception.Message -LogPath $launchLog
    exit 1
} finally {
    if ($null -ne $launcherMutex) {
        try {
            $launcherMutex.ReleaseMutex() | Out-Null
        } catch {
        }
        $launcherMutex.Dispose()
    }
}
