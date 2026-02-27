Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [switch]$VerifyShygazun
)

$launcher = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

Start-Process -FilePath $launcher -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "C:\DjinnOS\start-kernel.ps1"
Start-Sleep -Seconds 1
Start-Process -FilePath $launcher -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "C:\DjinnOS\start-atelier-api.ps1"
Start-Sleep -Seconds 1
Start-Process -FilePath $launcher -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "C:\DjinnOS\start-atelier-desktop.ps1"

if ($VerifyShygazun) {
    Start-Sleep -Seconds 4
    & "C:\DjinnOS\scripts\verify_shygazun_surfaces.ps1"
}
