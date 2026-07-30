@echo off
title FoodTrack Server (custom port)
cd /d "%~dp0backend"
set PORT=%1
if "%PORT%"=="" set PORT=8000
echo Starting FoodTrack Server on port %PORT%...
echo.
..\.venv\Scripts\python.exe run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%
    pause
)
