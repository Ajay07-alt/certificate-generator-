@echo off
title Visual Bulk Certificate Generator (Web Edition)
cd /d "B:\certificate web\1111"
echo Starting Visual Bulk Certificate Generator Web Server...
python server.py
if errorlevel 1 (
    echo.
    echo Server exited with error. Press any key to close.
    pause >nul
)
