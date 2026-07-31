
$orig = Get-Content ".env" -Raw
($orig -replace 'DATABASE_URL=sqlite\+aiosqlite:///\./foodtrack\.db', 'DATABASE_URL=sqlite+aiosqlite:///./fresh_test.db') | Set-Content ".env"
Remove-Item "fresh_test.db" -ErrorAction SilentlyContinue
Write-Host "=== Running alembic upgrade head on fresh DB ===" -ForegroundColor Cyan
venv\Scripts\python.exe -m alembic upgrade head
$exit = $LASTEXITCODE
$orig | Set-Content ".env"
Remove-Item "fresh_test.db" -ErrorAction SilentlyContinue
if ($exit -eq 0) { Write-Host "SUCCESS — migration chain is valid" -ForegroundColor Green }
else             { Write-Host "FAILED  — exit code $exit"          -ForegroundColor Red }
exit $exit
