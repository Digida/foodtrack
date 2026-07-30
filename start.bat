@echo off
title FoodTrack Server
cd /d "%~dp0backend"
echo Starting FoodTrack Server...
echo.
..\.venv\Scripts\python.exe run.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server exited with code %ERRORLEVEL%
    echo Check the output above for details.
    pause
)
