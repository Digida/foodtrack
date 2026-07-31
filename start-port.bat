@echo off
title FoodTrack — Development Server
cd /d "%~dp0"
set PORT=%1
if "%PORT%"=="" set PORT=8000
echo.
echo  Starting FoodTrack on port %PORT%...
echo.
.venv\Scripts\python.exe main.py --port %PORT% %2 %3 %4
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Server exited with code %ERRORLEVEL%
    pause
)
