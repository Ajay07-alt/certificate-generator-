@echo off
title Visual Bulk Certificate Generator
cd /d "B:\certificate web\1111"
echo Launching Visual Bulk Certificate Generator...
python main.py
if errorlevel 1 (
    echo.
    echo Application exited with error. Press any key to close.
    pause >nul
)
