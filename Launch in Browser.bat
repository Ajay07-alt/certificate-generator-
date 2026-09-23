@echo off
setlocal enabledelayedexpansion
title Visual Bulk Certificate Generator (Web Server Edition)
cd /d "%~dp0"

echo ========================================================
echo   VISUAL BULK CERTIFICATE GENERATOR (WEB SERVER)
echo ========================================================
echo.

:: 1. Detect Python command
set "PY_CMD="
python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
) else (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    ) else (
        py --version >nul 2>&1
        if not errorlevel 1 (
            set "PY_CMD=py"
        )
    )
)

:: 2. Handle missing Python
if "%PY_CMD%"=="" (
    echo [!] Python is not installed on this computer.
    echo [*] Automatically opening the Standalone Offline Web App in your browser...
    start "" "Open Offline App (No Python Needed).bat"
    exit /b 0
)

:: 3. Verify dependencies
echo [*] Checking Python libraries...
%PY_CMD% -c "import fastapi, uvicorn, PIL, pandas, openpyxl, fitz" >nul 2>&1
if errorlevel 1 (
    echo [*] First-time setup: Installing web server packages (FastAPI, Uvicorn, Pillow, pandas)...
    echo [*] Please wait a moment...
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [!] Failed to install Python server packages.
        echo [*] Falling back to Standalone Offline Browser App...
        start "" "Open Offline App (No Python Needed).bat"
        exit /b 0
    )
)

:: 4. Launch Web Server
echo [*] Starting FastAPI Web Server at http://127.0.0.1:8000 ...
%PY_CMD% server.py
if errorlevel 1 (
    echo.
    echo [!] Server stopped.
    pause
)
