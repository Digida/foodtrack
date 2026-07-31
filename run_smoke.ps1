$ErrorActionPreference = "Continue"
$base = "http://localhost:8000"

# Register (ignore if already exists)
try {
    Invoke-WebRequest "$base/api/v1/auth/register" -Method POST `
        -ContentType "application/json" `
        -Body '{"email":"smoke99@ft.dev","password":"SmokeRun1!","full_name":"Smoke"}' `
        -UseBasicParsing -TimeoutSec 10 | Out-Null
} catch {}

# Login
$lr  = Invoke-WebRequest "$base/api/v1/auth/login" -Method POST `
    -ContentType "application/json" `
    -Body '{"email":"smoke99@ft.dev","password":"SmokeRun1!"}' `
    -UseBasicParsing -TimeoutSec 10
$tok = ($lr.Content | ConvertFrom-Json).access_token
$h   = @{ Authorization = "Bearer $tok" }
Write-Host "Token: $($tok.Substring(0,20))..." -ForegroundColor Cyan

function Hit($path, $auth = $true, $xMin = 200, $xMax = 299) {
    $hdr = if ($auth) { $h } else { @{} }
    try {
        $code = (Invoke-WebRequest -Uri "$base$path" -Headers $hdr -UseBasicParsing -TimeoutSec 8).StatusCode
    } catch {
        $code = [int]($_.Exception.Response.StatusCode.value__)
        if ($code -eq 0) { $code = 999 }
    }
    $ok = ($code -ge $xMin -and $code -le $xMax)
    [PSCustomObject]@{ R = if ($ok) { "PASS" } else { "FAIL" }; Code = $code; Path = $path }
}

$results = [System.Collections.Generic.List[object]]::new()

# -- Public endpoints --
$results.Add((Hit "/health"                              $false))
$results.Add((Hit "/api/v1/tiers"                        $false))
$results.Add((Hit "/api/v1/search?q=apple"               $false))

# -- Authenticated endpoints --
$results.Add((Hit "/api/v1/auth/me"))
$results.Add((Hit "/metrics"))
$results.Add((Hit "/sla"))
$results.Add((Hit "/api/v1/taxonomy/nodes/1/items"))
$results.Add((Hit "/api/v1/taxonomy/items/grouped/by-category" $false))
$results.Add((Hit "/api/v1/products?page=1"))
$results.Add((Hit "/api/v1/batches?page=1"))
$results.Add((Hit "/api/v1/shipments?page=1"))
$results.Add((Hit "/api/v1/certificates?page=1"))
$results.Add((Hit "/api/v1/suppliers?page=1"))
$results.Add((Hit "/api/v1/suppliers/ranking/top"))
$results.Add((Hit "/api/v1/recalls?page=1"))
$results.Add((Hit "/api/v1/esg/summary"))
$results.Add((Hit "/api/v1/insurance/policies?page=1"))
$results.Add((Hit "/api/v1/insurance/claims?page=1"))
$results.Add((Hit "/api/v1/retention/policies"))
$results.Add((Hit "/api/v1/events/logs?page=1"))
$results.Add((Hit "/api/v1/telemetry/readings?page=1"))
$results.Add((Hit "/api/v1/telemetry/alerts?page=1"))
$results.Add((Hit "/api/v1/developer/api-keys"))
$results.Add((Hit "/api/v1/warehouses?page=1"))
$results.Add((Hit "/api/v1/analytics/items/top-moved"))
$results.Add((Hit "/api/v1/analytics/items/low-stock"))

# -- Auth boundary: no token must return 401 --
$results.Add((Hit "/metrics"                             $false 401 401))
$results.Add((Hit "/sla"                                 $false 401 401))
$results.Add((Hit "/api/v1/suppliers"                    $false 401 401))
$results.Add((Hit "/api/v1/recalls"                      $false 401 401))
$results.Add((Hit "/api/v1/esg/summary"                  $false 401 401))
$results.Add((Hit "/api/v1/events/logs"                  $false 401 401))
# telemetry/ingest is POST - unauthenticated POST should 401
try {
    $code = (Invoke-WebRequest -Uri "$base/api/v1/telemetry/ingest" -Method POST -ContentType "application/json" -Body '{}' -UseBasicParsing -TimeoutSec 8).StatusCode
} catch {
    $code = [int]($_.Exception.Response.StatusCode.value__)
}
$ok = ($code -eq 401)
$results.Add([PSCustomObject]@{ R = if ($ok) { "PASS" } else { "FAIL" }; Code = $code; Path = "POST /api/v1/telemetry/ingest (no auth=401)" })
$results.Add((Hit "/api/v1/certificates/by-item/1"       $false 401 401))

# -- Cert endpoints authed (404 ok - no seed data yet) --
$results.Add((Hit "/api/v1/certificates/by-item/1"       $true 200 404))
$results.Add((Hit "/api/v1/certificates/verify-chain/1"  $true 200 404))

# -- Print table --
$results | Format-Table R, Code, Path -AutoSize

$pass  = ($results | Where-Object { $_.R -eq "PASS" }).Count
$fail  = ($results | Where-Object { $_.R -eq "FAIL" }).Count
$total = $results.Count

Write-Host ""
Write-Host "=========================================" -ForegroundColor White
Write-Host "  Total : $total   PASS : $pass   FAIL : $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "=========================================" -ForegroundColor White

if ($fail -gt 0) {
    Write-Host "`nFailing tests:" -ForegroundColor Red
    $results | Where-Object { $_.R -eq "FAIL" } | ForEach-Object {
        Write-Host "  !! [$($_.Code)] $($_.Path)" -ForegroundColor Red
    }
}
