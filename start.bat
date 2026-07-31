@echo off
title FoodTrack — Development Server
cd /d "%~dp0"
echo.
echo  Starting FoodTrack (development mode)...
echo.
.venv\Scripts\python.exe main.py %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Server exited with code %ERRORLEVEL%
    pause
)
