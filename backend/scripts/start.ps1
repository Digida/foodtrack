param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $PSCommandPath
$ProjectRoot = Resolve-Path "$ScriptDir\.."
Set-Location $ProjectRoot

Write-Host "Installing dependencies..."
pip install -r requirements.txt

Write-Host "Running database migrations..."
alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Error "Migration failed"
    exit 1
}

if ($Reload) {
    Write-Host "Starting uvicorn with reload on $Host`:$Port"
    uvicorn app.main:app --host $Host --port $Port --reload
} else {
    Write-Host "Starting uvicorn on $Host`:$Port"
    uvicorn app.main:app --host $Host --port $Port
}
