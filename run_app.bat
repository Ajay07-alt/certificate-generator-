@echo off
title Visual Bulk Certificate Generator
cd /d "%~dp0"
echo Launching Visual Bulk Certificate Generator...
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)
