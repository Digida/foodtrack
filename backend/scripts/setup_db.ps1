param(
    [string]$DbName = "foodtrack",
    [string]$DbUser = "foodtrack",
    [string]$DbPass = "foodtrack_secret",
    [string]$Host = "localhost",
    [int]$Port = 5432
)

$ErrorActionPreference = "Stop"

$env:PGPASSWORD = $DbPass

Write-Host "Checking if PostgreSQL is reachable at $Host`:$Port..."
try {
    & "psql" -h $Host -p $Port -U postgres -c "SELECT 1" 2>&1 | Out-Null
} catch {
    Write-Warning "Could not connect to PostgreSQL. Make sure it's installed and running."
    exit 1
}

Write-Host "Creating database '$DbName'..."
& "psql" -h $Host -p $Port -U postgres -c "SELECT 1 FROM pg_database WHERE datname='$DbName'" | Select-String "1 row" | Out-Null
if ($LASTEXITCODE -ne 0) {
    & "psql" -h $Host -p $Port -U postgres -c "CREATE DATABASE $DbName"
    Write-Host "Database '$DbName' created."
} else {
    Write-Host "Database '$DbName' already exists."
}

Write-Host "Creating user '$DbUser'..."
& "psql" -h $Host -p $Port -U postgres -c "SELECT 1 FROM pg_roles WHERE rolname='$DbUser'" | Select-String "1 row" | Out-Null
if ($LASTEXITCODE -ne 0) {
    & "psql" -h $Host -p $Port -U postgres -c "CREATE USER $DbUser WITH PASSWORD '$DbPass'"
    Write-Host "User '$DbUser' created."
} else {
    Write-Host "User '$DbUser' already exists."
}

& "psql" -h $Host -p $Port -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DbName TO $DbUser"

Write-Host "Database setup complete. Update your backend/.env:"
Write-Host "  DATABASE_URL=postgresql+asyncpg://$DbUser`:$DbPass@$Host`:$Port/$DbName"
