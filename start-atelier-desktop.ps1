Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$desktopRoot = "C:\DjinnOS\apps\atelier-desktop"
if (-not (Test-Path $desktopRoot)) {
    throw "Atelier desktop path not found: $desktopRoot"
}

$npmPath = "C:\Program Files\nodejs\npm.cmd"
if (-not (Test-Path $npmPath)) {
    $cmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        $npmPath = $cmd.Source
    } else {
        throw "npm.cmd not found. Install Node.js or add npm.cmd to PATH."
    }
}

# Ensure Electron runs as Electron, not Node.
if (Test-Path Env:ELECTRON_RUN_AS_NODE) {
    Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
}

Set-Location $desktopRoot
& cmd.exe /c "`"$npmPath`" run dev"
