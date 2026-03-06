param(
    [string]$ExePath = "c:\DjinnOS\releases\KoLabyrnth-Setup.exe",
    [string]$Subject = "CN=KoLabyrnth Installer Signer"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "Installer EXE not found: $ExePath"
}

$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $Subject `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(2)

Set-AuthenticodeSignature -FilePath $ExePath -Certificate $cert | Out-Null

$sig = Get-AuthenticodeSignature -FilePath $ExePath
Write-Host ("signature_status: " + $sig.Status)
if ($sig.SignerCertificate) {
    Write-Host ("signer_subject: " + $sig.SignerCertificate.Subject)
    Write-Host ("signer_thumbprint: " + $sig.SignerCertificate.Thumbprint)
}
