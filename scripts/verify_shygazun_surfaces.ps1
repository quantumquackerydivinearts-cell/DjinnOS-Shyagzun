param(
    [string]$KernelBaseUrl = "http://127.0.0.1:8000",
    [string]$AtelierApiBaseUrl = "http://127.0.0.1:9000",
    [string]$Actor = "tester",
    [string]$ArtisanId = "artisan-1",
    [string]$Role = "artisan",
    [string]$WorkshopId = "workshop-1",
    [string]$CobraRoot = "C:\DjinnOS\apps\atelier-desktop\studio-cobra"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Json {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Url,
        [hashtable]$Headers = @{},
        [object]$Body = $null
    )
    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $Headers
        ContentType = "application/json"
        TimeoutSec = 20
    }
    if ($null -ne $Body) {
        $params["Body"] = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    return Invoke-RestMethod @params
}

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )
    if (-not $Condition) {
        throw "verification_failed: $Message"
    }
}

Write-Host "[verify] kernel events endpoint"
$events = Invoke-Json -Method GET -Url "$KernelBaseUrl/events"
Assert-True -Condition ($events -is [System.Array]) -Message "kernel /events did not return an array"

Write-Host "[verify] kernel akinenwun lookup determinism"
$lookupBody = @{
    akinenwun = "TyKoWuVu"
    mode = "prose"
    ingest = $true
}
$lookupA = Invoke-Json -Method POST -Url "$KernelBaseUrl/v0.1/akinenwun/lookup" -Body $lookupBody
$lookupB = Invoke-Json -Method POST -Url "$KernelBaseUrl/v0.1/akinenwun/lookup" -Body @{
    akinenwun = "TyKoWuVu"
    mode = "prose"
    ingest = $false
}
Assert-True -Condition ([string]$lookupA.frontier_hash -eq [string]$lookupB.frontier_hash) -Message "kernel frontier_hash drifted for same akinenwun"

Write-Host "[verify] atelier api health + ambroflow lookup"
$headers = @{
    "X-Atelier-Actor" = $Actor
    "X-Atelier-Capabilities" = "kernel.observe"
    "X-Artisan-Id" = $ArtisanId
    "X-Artisan-Role" = $Role
    "X-Workshop-Id" = $WorkshopId
    "X-Workshop-Scopes" = "scene:*,workspace:*"
}
$health = Invoke-Json -Method GET -Url "$AtelierApiBaseUrl/health" -Headers $headers
Assert-True -Condition ([string]$health.status -eq "ok") -Message "atelier api health failed"
$ambroLookup = Invoke-Json -Method POST -Url "$AtelierApiBaseUrl/v1/ambroflow/akinenwun/lookup" -Headers $headers -Body @{
    akinenwun = "TyKoWuVu"
    mode = "prose"
    ingest = $false
}
Assert-True -Condition ([string]$ambroLookup.frontier_hash -eq [string]$lookupB.frontier_hash) -Message "atelier lookup frontier_hash mismatch vs kernel"

Write-Host "[verify] cobra compiler path"
$pyCmd = @'
from qqva.shygazun_compiler import compile_akinenwun_to_ir
ir = compile_akinenwun_to_ir("TyKoWuVu")
assert ir["canonical_compound"] == "TyKoWuVu"
assert len(ir["symbols"]) == 4
'@
& py -c $pyCmd
if ($LASTEXITCODE -ne 0) {
    throw "verification_failed: python cobra compiler check failed"
}

Write-Host "[verify] studio hub cobra filesystem path"
if (-not (Test-Path $CobraRoot)) {
    New-Item -ItemType Directory -Path $CobraRoot -Force | Out-Null
}
$probePath = Join-Path $CobraRoot "_verify_probe.cobra"
$probeText = "entity verify_01 0 0 probe`n  lex TyKoWuVu`n"
Set-Content -LiteralPath $probePath -Value $probeText -NoNewline
$roundtrip = Get-Content -LiteralPath $probePath -Raw
Assert-True -Condition ($roundtrip -eq $probeText) -Message "cobra file roundtrip mismatch"
Remove-Item -LiteralPath $probePath -Force -ErrorAction SilentlyContinue

Write-Host "[verify] renderer lab ingestion hooks present"
$appJsx = "C:\DjinnOS\apps\atelier-desktop\src\App.jsx"
Assert-True -Condition (Test-Path $appJsx) -Message "renderer source missing"
$hasCobraParser = Select-String -LiteralPath $appJsx -Pattern "parseCobraShygazunScript|parseCobraShygazun" -SimpleMatch:$false
$hasLexSupport = Select-String -LiteralPath $appJsx -Pattern "lex|akinenwun|shygazun" -SimpleMatch:$false
Assert-True -Condition ($hasCobraParser.Count -gt 0) -Message "renderer missing cobra parser hook"
Assert-True -Condition ($hasLexSupport.Count -gt 0) -Message "renderer missing shygazun lexical hook"

Write-Host "[verify] shygazun surfaces OK"
