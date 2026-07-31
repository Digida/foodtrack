#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the FoodTrack platform.
.DESCRIPTION
    Delegates to main.py — the single authoritative launcher.
    Pass any arguments supported by main.py.
.EXAMPLE
    .\start.ps1                    # dev mode
    .\start.ps1 --prod             # production mode
    .\start.ps1 --port 9000        # custom port
    .\start.ps1 --skip-migrate     # skip migrations
#>
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)

Set-Location $PSScriptRoot

$python = if (Test-Path ".venv\Scripts\python.exe") {
    ".venv\Scripts\python.exe"
} elseif (Test-Path "backend\venv\Scripts\python.exe") {
    "backend\venv\Scripts\python.exe"
} else {
    "python"
}

& $python main.py @Args
