@echo off
setlocal enabledelayedexpansion
title Visual Bulk Certificate Generator (Desktop Edition)
cd /d "%~dp0"

echo ========================================================
echo   VISUAL BULK CERTIFICATE GENERATOR (OFFLINE EDITION)
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
    echo [!] Python is not detected on your system.
    echo.
    echo --------------------------------------------------------
    echo  Good news: You can use this app WITHOUT Python!
    echo --------------------------------------------------------
    echo  Double-click "Open Offline App (No Python Needed).bat"
    echo  to generate certificates directly in your web browser!
    echo --------------------------------------------------------
    echo.
    set /p "CHOICE=Open offline browser app now? (Y/n): "
    if /i "!CHOICE!"=="n" (
        exit /b 1
    )
    start "" "Open Offline App (No Python Needed).bat"
    exit /b 0
)

:: 3. Verify and auto-install required dependencies
echo [*] Checking required Python packages...
%PY_CMD% -c "import PIL, pandas, openpyxl, fitz" >nul 2>&1
if errorlevel 1 (
    echo [*] First-time setup: Installing required libraries (Pillow, pandas, openpyxl, PyMuPDF)...
    echo [*] Please wait while dependencies are downloaded and installed...
    echo.
    %PY_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [!] Failed to install dependencies automatically.
        echo [*] You can still use the app offline without Python by running:
        echo     "Open Offline App (No Python Needed).bat"
        echo.
        pause
        exit /b 1
    )
)

:: 4. Launch Desktop GUI
echo [*] Starting Certificate Generator Desktop App...
echo.
%PY_CMD% main.py
if errorlevel 1 (
    echo.
    echo [!] Application exited with an error.
    echo [*] Tip: You can also use the web app: "Open Offline App (No Python Needed).bat"
    echo.
    pause
)
