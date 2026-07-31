param([string]$Token = "")

$base = "http://localhost:8000"
$h = @{}
if ($Token) { $h["Authorization"] = "Bearer $Token" }
$ph = @{}  # public (no auth)

$tests = @(
    @{ Path="/health";                            Auth=$false; Label="GET /health (public)" }
    @{ Path="/metrics";                           Auth=$true;  Label="GET /metrics" }
    @{ Path="/sla";                               Auth=$true;  Label="GET /sla" }
    @{ Path="/metrics";                           Auth=$false; Expect=401; Label="GET /metrics (no auth=401)" }
    @{ Path="/api/v1/auth/me";                    Auth=$true;  Label="GET /auth/me" }
    @{ Path="/api/v1/tiers";                      Auth=$false; Label="GET /tiers (public)" }
    @{ Path="/api/v1/search?q=apple";             Auth=$false; Label="GET /search (public)" }
    @{ Path="/api/v1/taxonomy/items";             Auth=$true;  Label="GET /taxonomy/items" }
    @{ Path="/api/v1/products";                   Auth=$true;  Label="GET /products" }
    @{ Path="/api/v1/batches";                    Auth=$true;  Label="GET /batches" }
    @{ Path="/api/v1/shipments";                  Auth=$true;  Label="GET /shipments" }
    @{ Path="/api/v1/certificates";               Auth=$true;  Label="GET /certificates" }
    @{ Path="/api/v1/certificates/by-item/1";     Auth=$true;  Expect=404; Label="GET /certificates/by-item/1 (authed, 404 ok)" }
    @{ Path="/api/v1/certificates/by-item/1";     Auth=$false; Expect=401; Label="GET /certificates/by-item/1 (no auth=401)" }
    @{ Path="/api/v1/suppliers";                  Auth=$true;  Label="GET /suppliers" }
    @{ Path="/api/v1/suppliers/ranking/top";      Auth=$true;  Label="GET /suppliers/ranking/top" }
    @{ Path="/api/v1/suppliers";                  Auth=$false; Expect=401; Label="GET /suppliers (no auth=401)" }
    @{ Path="/api/v1/recalls";                    Auth=$true;  Label="GET /recalls" }
    @{ Path="/api/v1/recalls";                    Auth=$false; Expect=401; Label="GET /recalls (no auth=401)" }
    @{ Path="/api/v1/esg/summary";                Auth=$true;  Label="GET /esg/summary" }
    @{ Path="/api/v1/esg/summary";                Auth=$false; Expect=401; Label="GET /esg/summary (no auth=401)" }
    @{ Path="/api/v1/insurance/policies";         Auth=$true;  Label="GET /insurance/policies" }
    @{ Path="/api/v1/insurance/claims";           Auth=$true;  Label="GET /insurance/claims" }
    @{ Path="/api/v1/retention/policies";         Auth=$true;  Label="GET /retention/policies" }
    @{ Path="/api/v1/events/logs";                Auth=$true;  Label="GET /events/logs" }
    @{ Path="/api/v1/events/logs";                Auth=$false; Expect=401; Label="GET /events/logs (no auth=401)" }
    @{ Path="/api/v1/telemetry/readings";         Auth=$true;  Label="GET /telemetry/readings" }
    @{ Path="/api/v1/telemetry/alerts";           Auth=$true;  Label="GET /telemetry/alerts" }
    @{ Path="/api/v1/developer/api-keys";         Auth=$true;  Label="GET /developer/api-keys" }
    @{ Path="/api/v1/inventory";                  Auth=$true;  Label="GET /inventory" }
    @{ Path="/api/v1/warehouses";                 Auth=$true;  Label="GET /warehouses" }
)

$pass = 0
$fail = 0
$rows = @()

foreach ($t in $tests) {
    $headers = if ($t.Auth) { $h } else { $ph }
    $expect  = if ($t.ContainsKey("Expect")) { $t.Expect } else { 200 }
    $expectMax = if ($t.ContainsKey("Expect")) { $t.Expect } else { 299 }

    try {
        $resp = Invoke-WebRequest -Uri "$base$($t.Path)" -Headers $headers -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
        $code = $resp.StatusCode
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if (-not $code) { $code = 0 }
    }

    $ok = ($code -ge $expect -and $code -le $expectMax)
    if ($ok) { $pass++ } else { $fail++ }

    $rows += [PSCustomObject]@{
        Result = if ($ok) { "PASS" } else { "FAIL" }
        Code   = $code
        Test   = $t.Label
    }
}

$rows | Format-Table -AutoSize

Write-Output ""
Write-Output "========================================="
Write-Output "  Total : $($tests.Count)   PASS : $pass   FAIL : $fail"
Write-Output "========================================="
if ($fail -gt 0) {
    Write-Output ""
    Write-Output "Failing tests:"
    $rows | Where-Object { $_.Result -eq "FAIL" } | ForEach-Object {
        Write-Output "  FAIL [$($_.Code)] $($_.Test)"
    }
}
