param(
    [string]$Command = "upgrade",
    [string]$Revision = "head"
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot\..

Write-Host "Running alembic $Command $Revision..."
alembic $Command $Revision

if ($LASTEXITCODE -ne 0) {
    Write-Error "Migration failed"
    exit 1
}

Write-Host "Migration $Command $Revision completed successfully"
